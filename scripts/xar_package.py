"""Minimal unsigned Apple flat-package writer/reader, using documented XAR/newc.

Used to produce an inspectable pkg on Windows when a Mac runner is unavailable.
The native macOS pipeline remains authoritative for native package validation.
"""
from pathlib import Path
import gzip
import hashlib
import struct
import zlib
import xml.etree.ElementTree as ET


def read_xar(path):
    raw = Path(path).read_bytes()
    magic, header_size, version, compressed_size, size, algorithm = struct.unpack_from(">4sHHQQI", raw)
    assert magic == b"xar!" and version == 1
    compressed_toc = raw[header_size:header_size + compressed_size]
    toc = zlib.decompress(compressed_toc)
    assert len(toc) == size
    tree = ET.fromstring(toc).find("toc")
    heap = raw[header_size + compressed_size:]
    checksum = tree.find("checksum")
    if algorithm == 1:
        offset = int(checksum.findtext("offset"))
        assert heap[offset:offset + 20] == hashlib.sha1(compressed_toc).digest()
    files = {}

    def walk(nodes, prefix=""):
        for node in nodes:
            name = prefix + node.findtext("name")
            if node.findtext("type") == "directory":
                walk(node.findall("file"), name + "/")
                continue
            data = node.find("data")
            if data is None:
                continue
            offset, length = int(data.findtext("offset")), int(data.findtext("length"))
            archived = heap[offset:offset + length]
            archived_sum = data.find("archived-checksum")
            if archived_sum is not None and archived_sum.attrib.get("style") == "sha1":
                assert hashlib.sha1(archived).hexdigest() == archived_sum.text
            style = data.find("encoding").attrib["style"]
            if style == "application/octet-stream":
                extracted = archived
            elif style == "application/x-gzip":
                extracted = zlib.decompress(archived)
            else:
                raise ValueError(f"Unsupported XAR encoding: {style}")
            assert len(extracted) == int(data.findtext("size"))
            extracted_sum = data.find("extracted-checksum")
            if extracted_sum is not None and extracted_sum.attrib.get("style") == "sha1":
                assert hashlib.sha1(extracted).hexdigest() == extracted_sum.text
            files[name] = extracted
    walk(tree.findall("file"))
    return files


def write_xar(path, files):
    root = ET.Element("xar")
    toc = ET.SubElement(root, "toc")
    checksum = ET.SubElement(toc, "checksum", {"style": "sha1"})
    ET.SubElement(checksum, "offset").text = "0"
    ET.SubElement(checksum, "size").text = "20"
    heap = bytearray(b"\0" * 20)
    directories = {"": toc}
    inode = 1
    for filename, content in sorted(files.items()):
        parent = ""
        parts = filename.split("/")
        assert all(p not in ("", ".", "..") for p in parts)
        for part in parts[:-1]:
            name = parent + part + "/"
            if name not in directories:
                node = ET.SubElement(directories[parent], "file", {"id": str(inode)})
                inode += 1
                ET.SubElement(node, "name").text = part
                ET.SubElement(node, "type").text = "directory"
                ET.SubElement(node, "mode").text = "0755"
                directories[name] = node
            parent = name
        node = ET.SubElement(directories[parent], "file", {"id": str(inode)})
        inode += 1
        ET.SubElement(node, "name").text = parts[-1]
        ET.SubElement(node, "type").text = "file"
        ET.SubElement(node, "mode").text = "0644"
        data = ET.SubElement(node, "data")
        ET.SubElement(data, "length").text = str(len(content))
        ET.SubElement(data, "offset").text = str(len(heap))
        ET.SubElement(data, "size").text = str(len(content))
        ET.SubElement(data, "encoding", {"style": "application/octet-stream"})
        for tag in ["archived-checksum", "extracted-checksum"]:
            ET.SubElement(data, tag, {"style": "sha1"}).text = hashlib.sha1(content).hexdigest()
        heap.extend(content)
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    compressed = zlib.compress(xml, 9)
    heap[:20] = hashlib.sha1(compressed).digest()
    header = struct.pack(">4sHHQQI", b"xar!", 28, 1, len(compressed), len(xml), 1)
    Path(path).write_bytes(header + compressed + heap)
    assert read_xar(path) == files


def cpio_gzip(root):
    """cpio newc with root ownership, deterministic metadata and executable scripts."""
    archive = bytearray()
    inode = 1

    def entry(name, data, mode):
        nonlocal inode
        name = name.encode("utf-8") + b"\0"
        fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
        header = b"070701" + b"".join(f"{n:08x}".encode("ascii") for n in fields)
        archive.extend(header + name)
        archive.extend(b"\0" * (-len(archive) % 4))
        archive.extend(data)
        archive.extend(b"\0" * (-len(archive) % 4))
        inode += 1
    entry(".", b"", 0o040755)
    for path in sorted(Path(root).rglob("*")):
        name = "./" + path.relative_to(root).as_posix()
        if path.is_dir():
            entry(name, b"", 0o040755)
        else:
            mode = 0o100755 if path.name == "postinstall" or path.suffix == ".command" else 0o100644
            entry(name, path.read_bytes(), mode)
    entry("TRAILER!!!", b"", 0)
    archive.extend(b"\0" * (-len(archive) % 512))
    return gzip.compress(bytes(archive), compresslevel=9, mtime=0)
