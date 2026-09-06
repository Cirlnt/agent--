import anthropic, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = anthropic.Anthropic()
with c.messages.stream(model="deepseek-v4-flash", max_tokens=16,
                       thinking={"type": "disabled"},
                       messages=[{"role": "user", "content": "请写一篇 300 字散文《窗外》"}]) as s:
    for ch in s.text_stream:
        print(ch, end="", flush=True)
    fin = s.get_final_message()
print(f"\nstop_reason={fin.stop_reason}")