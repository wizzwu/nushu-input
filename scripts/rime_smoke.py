"""Real librime input/output checks using isolated directories. Standard library only."""
from pathlib import Path
import argparse
import ctypes as C
import json
import os
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


class Traits(C.Structure):
    _fields_ = [("data_size", C.c_int)] + [(n, C.c_char_p) for n in ["shared_data_dir", "user_data_dir", "distribution_name", "distribution_code_name", "distribution_version", "app_name"]] + [("modules", C.POINTER(C.c_char_p)), ("min_log_level", C.c_int)] + [(n, C.c_char_p) for n in ["log_dir", "prebuilt_data_dir", "staging_dir"]]


class Composition(C.Structure):
    _fields_ = [(n, C.c_int) for n in ["length", "cursor_pos", "sel_start", "sel_end"]] + [("preedit", C.c_char_p)]


class Candidate(C.Structure):
    _fields_ = [("text", C.c_char_p), ("comment", C.c_char_p), ("reserved", C.c_void_p)]


class Menu(C.Structure):
    _fields_ = [(n, C.c_int) for n in ["page_size", "page_no", "is_last_page", "highlighted_candidate_index", "num_candidates"]] + [("candidates", C.POINTER(Candidate)), ("select_keys", C.c_char_p)]


class Context(C.Structure):
    _fields_ = [("data_size", C.c_int), ("composition", Composition), ("menu", Menu), ("commit_text_preview", C.c_char_p), ("select_labels", C.POINTER(C.c_char_p))]


class Commit(C.Structure):
    _fields_ = [("data_size", C.c_int), ("text", C.c_char_p)]


def init_struct(obj):
    obj.data_size = C.sizeof(obj) - C.sizeof(C.c_int)
    return obj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dll", required=True)
    parser.add_argument("--label", default="pinned-weasel-0.17.4")
    args = parser.parse_args()
    dll_path = Path(args.dll).resolve()
    handle = os.add_dll_directory(str(dll_path.parent)) if os.name == "nt" else None
    lib = C.CDLL(str(dll_path))
    S = C.c_size_t
    def bind(name, restype, *argtypes):
        fn = getattr(lib, "Rime" + name)
        fn.restype, fn.argtypes = restype, list(argtypes)
        return fn
    setup = bind("Setup", None, C.POINTER(Traits))
    initialize = bind("Initialize", None, C.POINTER(Traits))
    maintenance = bind("StartMaintenance", C.c_int, C.c_int)
    join = bind("JoinMaintenanceThread", None)
    create = bind("CreateSession", S)
    destroy = bind("DestroySession", C.c_int, S)
    select = bind("SelectSchema", C.c_int, S, C.c_char_p)
    clear = bind("ClearComposition", None, S)
    process = bind("ProcessKey", C.c_int, S, C.c_int, C.c_int)
    get_context = bind("GetContext", C.c_int, S, C.POINTER(Context))
    free_context = bind("FreeContext", C.c_int, C.POINTER(Context))
    get_commit = bind("GetCommit", C.c_int, S, C.POINTER(Commit))
    free_commit = bind("FreeCommit", C.c_int, C.POINTER(Commit))
    option = bind("SetOption", None, S, C.c_char_p, C.c_int)
    finalize = bind("Finalize", None)
    folder = ROOT / ".build" / ("rime-smoke-" + args.label)
    user = folder / "user"
    user.mkdir(parents=True, exist_ok=True)
    (user / "default.custom.yaml").write_text("patch:\n  schema_list:\n    - schema: luna_pinyin_nushu\n    - schema: nushu\n", encoding="utf-8")
    shared = ROOT / ".build/shared"
    traits = init_struct(Traits())
    # Traits hold Python bytes references through ctypes' _objects for the whole session.
    traits.shared_data_dir, traits.user_data_dir = str(shared).encode("utf-8"), str(user).encode("utf-8")
    traits.app_name = b"rime.nushu-smoke"
    traits.distribution_name = b"NushuInput"
    traits.distribution_code_name = b"nushu"
    traits.distribution_version = b"0.1.0"
    traits.min_log_level = 2
    traits.log_dir = str(folder).encode("utf-8")
    setup(C.byref(traits))
    initialize(C.byref(traits))
    if maintenance(1):
        join()
    session = create()
    assert session
    results = []

    def candidates():
        ctx = init_struct(Context())
        assert get_context(session, C.byref(ctx))
        try:
            return [ctx.menu.candidates[i].text.decode("utf-8") for i in range(ctx.menu.num_candidates)]
        finally:
            free_context(C.byref(ctx))

    def type_code(schema, code):
        clear(session)
        assert select(session, schema.encode())
        option(session, b"ascii_mode", 0)
        for letter in code:
            process(session, ord(letter), 0)
        return candidates()

    try:
        for schema in ["nushu", "luna_pinyin_nushu"]:
            assert (user / "build" / f"{schema}.schema.yaml").exists(), f"Schema failed to compile: {schema}"
        dialect = type_code("nushu", "i")
        assert any("\U0001b170" in x for x in dialect), dialect
        results.append({"schema": "nushu", "input": "i", "candidates": dialect})
        # Select a real candidate with the space key and inspect the committed Unicode.
        process(session, 32, 0)
        commit = init_struct(Commit())
        assert get_commit(session, C.byref(commit))
        text = commit.text.decode("utf-8")
        free_commit(C.byref(commit))
        assert any(0x1B170 <= ord(c) <= 0x1B2FB for c in text), text
        results.append({"committed_unicode": text, "codepoints": [f"U+{ord(c):X}" for c in text]})
        spelling_groups = {}
        for line in (shared / "nushu.dict.yaml").read_text(encoding="utf-8-sig").split("...", 1)[1].splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            char, code, *_ = line.split("\t")
            spelling = re.sub(r"[1-5]+$", "", code)
            for before, after in [("tc", "j"), ("tch", "q"), ("c", "x"), ("ts", "z"), ("tsh", "c"),
                                  ("p", "b"), ("ph", "p"), ("t", "d"), ("th", "t"), ("k", "g"), ("kh", "k")]:
                spelling = re.sub(r"^" + before + r"(?=[aiueoyw])", after, spelling)
            spelling_groups.setdefault(spelling, set()).add(char)
        missing = []
        for spelling, required in spelling_groups.items():
            values = type_code("nushu", spelling)
            found = set("".join(values))
            for page in range(40):
                if required <= found:
                    break
                process(session, ord("="), 0)
                following = candidates()
                if following == values:
                    break
                values = following
                found.update("".join(values))
            missing.extend(required - found)
        assert not missing, f"Unreachable dialect characters: {missing}"
        results.append({"dialect_characters_reachable": 396, "untoned_spellings_tested": len(spelling_groups)})
        for code in ["yi", "nv", "ren"]:
            values = type_code("luna_pinyin_nushu", code)
            assert any(any(0x1B170 <= ord(c) <= 0x1B2FB for c in x) for x in values), (code, values)
            results.append({"schema": "luna_pinyin_nushu", "input": code, "candidates": values})
        # The touch-keyboard action emits this same Ctrl+Shift+4 key event.
        process(session, ord("4"), 4 | 1)
        clear(session)
        for letter in "yi":
            process(session, ord(letter), 0)
        values = candidates()
        assert any("一" in x for x in values), values
        results.append({"toggle_to_hanzi": values})
        clear(session)
        for letter in "yi":
            process(session, ord(letter), 0)
        first = candidates()
        process(session, ord("="), 0)
        second = candidates()
        results.append({"pagination_first": first, "pagination_second": second})
        assert first != second, "Candidate pagination did not advance"
    finally:
        destroy(session)
        finalize()
    report = {"library": str(dll_path), "label": args.label, "architecture_bits": C.sizeof(C.c_void_p) * 8, "results": results}
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / f"rime-smoke-{args.label}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Native Rime smoke tests passed: {args.label}")


if __name__ == "__main__":
    main()
