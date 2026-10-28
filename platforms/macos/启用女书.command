#!/bin/bash
set -eu
BASE="$(cd "$(dirname "$0")" && pwd)"
if /usr/bin/ruby "$BASE/configure.rb"; then
  echo '女书配置完成。请退出账户重新登录，必要时在系统设置中添加鼠须管。'
else
  echo '配置失败，详情：~/Library/Logs/NushuInput-install.log'
  exit 1
fi
