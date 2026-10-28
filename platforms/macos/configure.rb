#!/usr/bin/ruby
# Ruby/Psych ship with macOS 13+. Runs as the desktop user, never as root.
require 'yaml'
require 'fileutils'
require 'time'

abort '请以桌面登录用户运行此工具。' if Process.uid == 0
base = File.expand_path(File.dirname(__FILE__))
user = File.join(Dir.home, 'Library', 'Rime')
backup = File.join(user, 'nushu-backups', Time.now.strftime('%Y%m%d-%H%M%S-%6N'))
FileUtils.mkdir_p(File.join(Dir.home, 'Library', 'Logs'))
log = File.open(File.join(Dir.home, 'Library', 'Logs', 'NushuInput-install.log'), 'a')
$stdout.reopen(log)
$stderr.reopen(log)
puts "#{Time.now.iso8601} 开始配置女书"

def mapping(path)
  return {} unless File.exist?(path)
  raw = File.read(path, :encoding => 'UTF-8').sub(/^\uFEFF/, '')
  data = if Psych::VERSION.to_i >= 4
    Psych.safe_load(raw, :permitted_classes => [], :aliases => true)
  else
    Psych.safe_load(raw, [], [], true)
  end
  data ||= {}
  raise "配置格式无效，已停止：#{path}" unless data.is_a?(Hash)
  data
end

begin
  default_path = File.join(user, 'default.custom.yaml')
  config = mapping(default_path)
  config['patch'] ||= {}
  patch = config['patch']
  raise 'patch 必须为映射' unless patch.is_a?(Hash)
  raise '存在高级 schema_list 补丁，请先手动整理方案列表。原配置未更改。' if patch.keys.any? { |k| k.to_s.start_with?('schema_list/') }
  fallback = mapping(File.join(user, 'build', 'default.yaml'))
  fallback = mapping(File.join(base, 'shared', 'default.yaml')) if fallback.empty?
  old = patch.fetch('schema_list', fallback.fetch('schema_list', [])) || []
  raise 'schema_list 必须为列表' unless old.is_a?(Array)
  ids = ['luna_pinyin_nushu', 'nushu']
  patch['schema_list'] = ids.map { |id| {'schema' => id} } + old.reject { |item| item.is_a?(Hash) && ids.include?(item['schema']) }
  writes = {default_path => YAML.dump(config)}
  ids.each do |id|
    path = File.join(user, "#{id}.custom.yaml")
    data = mapping(path)
    data['patch'] ||= {}
    raise "无效 patch：#{path}" unless data['patch'].is_a?(Hash)
    data['patch']['style/font_face'] = 'NotoSansNushu-Regular'
    data['patch']['style/comment_font_face'] = 'PingFangSC-Regular'
    data['patch']['schema/name'] = id == 'nushu' ? '女书·江永方言拼音' : '女书·普通话拼音'
    writes[path] = YAML.dump(data)
  end
  FileUtils.mkdir_p(backup)
  source_root = File.join(base, 'shared')
  owned = ['nushu.dict.yaml', 'nushu.schema.yaml', 'luna_pinyin_nushu.schema.yaml', 's2nushu.txt', 's2nushu.json']
  Dir.glob(File.join(source_root, '**', '*')).each do |source|
    next unless File.file?(source)
    relative = source.delete_prefix(source_root + '/')
    target = File.join(user, relative)
    next if File.exist?(target) && !owned.include?(File.basename(source))
    writes[target] = File.binread(source)
  end
  writes.each do |target, content|
    if File.exist?(target)
      saved = File.join(backup, target.delete_prefix(user + '/'))
      FileUtils.mkdir_p(File.dirname(saved))
      FileUtils.cp(target, saved)
    end
    FileUtils.mkdir_p(File.dirname(target))
    File.binwrite(target + '.nushu-tmp', content)
    File.rename(target + '.nushu-tmp', target)
  end
  # Deploy into an isolated current working directory using Squirrel's builder.
  squirrel = '/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel'
  Dir.chdir(user) { raise '女书字典编译失败' unless system(squirrel, '--build') }
  ids.each do |id|
    raise "未生成编译方案：#{id}" unless File.exist?(File.join(user, 'build', "#{id}.schema.yaml"))
  end
  system(squirrel, '--reload')
  puts "配置完成，备份：#{backup}。请退出账户重新登录，并在系统设置中添加鼠须管。"
rescue => e
  warn "#{e.class}: #{e.message}\n#{e.backtrace.join("\n")}"
  exit 1
end
