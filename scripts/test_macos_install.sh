#!/bin/bash
# Run only on a disposable macOS GitHub runner, never the developer's desktop.
set -eu
if [ "${GITHUB_ACTIONS:-}" != true ] || [ "${RUNNER_OS:-}" != macOS ]; then
  echo 'This system installation test is restricted to disposable macOS GitHub runners.' >&2
  exit 1
fi
sudo /usr/sbin/installer -pkg "$PWD/dist/NushuInput.pkg" -target /
test -f '/Library/Fonts/NotoSansNushu-Regular.ttf'
if ! /usr/bin/ruby '/Library/Application Support/NushuInput/configure.rb'; then
  /usr/bin/tail -100 "$HOME/Library/Logs/NushuInput-install.log"
  exit 1
fi
test -f "$HOME/Library/Rime/build/nushu.schema.yaml"
test -f "$HOME/Library/Rime/build/luna_pinyin_nushu.schema.yaml"
python scripts/rime_smoke.py --dll '/Library/Input Methods/Squirrel.app/Contents/Frameworks/librime.1.dylib' --label native-macos
