package org.nushuinput.smoketest;

import android.app.Activity;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(24, 40, 24, 0);
        TextView title = new TextView(this);
        title.setText("女书离线输入测试：输入 nv，按空格选字\n此测试编辑器已加载女书字体");
        title.setTextSize(20);
        layout.addView(title);
        final EditText editor = new EditText(this);
        editor.setSingleLine(false);
        editor.setMinLines(3);
        editor.setTextSize(32);
        editor.setTypeface(android.graphics.Typeface.createFromAsset(getAssets(), "NotoSansNushu-Regular.ttf"));
        editor.setHint("女书输出区");
        editor.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                StringBuilder hex = new StringBuilder();
                for (int i = 0; i < s.length();) {
                    int code = Character.codePointAt(s, i);
                    hex.append(String.format("U+%X ", code));
                    i += Character.charCount(code);
                }
                android.util.Log.i("NushuFixture", "TEXT=" + s + " CODEPOINTS=" + hex);
                android.content.ClipboardManager clipboard =
                    (android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
                clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Nushu test", s));
                boolean same = s.toString().equals(clipboard.getPrimaryClip().getItemAt(0).getText().toString());
                android.util.Log.i("NushuFixture", "CLIPBOARD_ROUNDTRIP=" + same);
            }
            public void afterTextChanged(Editable s) {}
        });
        layout.addView(editor);
        setContentView(layout);
        editor.requestFocus();
        editor.postDelayed(new Runnable() {
            public void run() {
                ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE))
                    .showSoftInput(editor, InputMethodManager.SHOW_IMPLICIT);
            }
        }, 1000);
    }
}
