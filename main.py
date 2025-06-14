import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, PostbackAction,
    QuickReply, QuickReplyButton
)

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler      = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# -------------------- ตารางตัดสินรางวัล --------------------
DECISION = {
    ("A1","B1","C1"): "นวัตกรรมการบริการ",
    ("A1","B3","C1"): "นวัตกรรมการบริการ",
    ("A1","B3","C2"): "ขยายผลมาตรฐานการบริการ",
    ("A1","B1","C3"): "บูรณาการข้อมูลในรูปแบบดิจิทัล",
    ("A1","B3","C3"): "บูรณาการข้อมูลในรูปแบบดิจิทัล",
    ("A1","B1","C4"): "บริการตอบโจทย์ตรงใจ",
    ("A1","B3","C4"): "บริการตอบโจทย์ตรงใจ",
    ("A1","B1","C5"): "ยกระดับการอำนวยความสะดวกในการให้บริการ",
    ("A1","B3","C5"): "ยกระดับการอำนวยความสะดวกในการให้บริการ",
    ("A1","B3","C6"): "ขับเคลื่อนเห็นผล",
    ("A2","B1","C7"): "สัมฤทธิผลประชาชนมีส่วนร่วม",
    ("A2","B3","C7"): "สัมฤทธิผลประชาชนมีส่วนร่วม",
    ("A2","B3","C2"): "เลื่องลือขยายผล"
}

# -------------------- ช่วยสร้าง Quick Reply --------------------
def qr(btns):
    return QuickReply(items=[
        QuickReplyButton(action=PostbackAction(label=l, data=d, display_text=l))
        for l, d in btns
    ])

# -------------------- จัดการ state --------------------
user_state = {}            # {uid: {"step":…, "A":…, "B":…, "C":…}}
def reset(uid):
    user_state[uid] = {"step": 0, "A": None, "B": None, "C": None}

# -------------------- Webhook --------------------
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body      = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# -------------------- เมื่อได้รับ “ข้อความ” --------------------
@handler.add(MessageEvent, message=TextMessage)
def on_text(event):
    uid  = event.source.user_id
    text = event.message.text.strip()

    if text.lower() in ("เริ่ม", "เริ่มใหม่", "reset"):
        reset(uid); ask_q1(event.reply_token); return

    if uid not in user_state:
        reset(uid); ask_q1(event.reply_token); return

    # ถ้าไม่ใช่ปุ่มที่เรากำหนด
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage('โปรดเลือกจากปุ่มที่กำหนด หรือพิมพ์ "เริ่ม" เพื่อเริ่มใหม่')
    )

# -------------------- เมื่อกด Postback --------------------
@handler.add(PostbackEvent)
def on_postback(event):
    uid  = event.source.user_id
    data = event.postback.data
    st   = user_state.get(uid)
    if not st:                 # ยังไม่เคยมี state
        reset(uid); st = user_state[uid]

    # ----------- Q1 -----------
    if st["step"] == 0 and data.startswith("A"):
        st["A"]   = data
        st["step"] = 1
        if data == "A3":       # เข้ากลุ่ม PMQA จบเลย
            reply_done(event.reply_token, "PMQA")
            reset(uid)
            return
        ask_q2(event.reply_token)
        return

    # ----------- Q2 -----------
    if st["step"] == 1 and data.startswith("B"):
        if data == "B0":       # < 1 ปี   ไม่เข้าเกณฑ์
            reply_done(event.reply_token, "ผลงานต้องดำเนินการไม่น้อยกว่า 1 ปี")
            reset(uid); return
        st["B"]   = data
        st["step"] = 2
        ask_q3(event.reply_token)
        return

    # ----------- Q3 -----------
    if st["step"] == 2 and data.startswith("C"):
        st["C"] = data
        result  = DECISION.get(
            (st["A"], st["B"], st["C"]),
            "ยังไม่พบประเภทที่ตรง โปรดปรึกษาเจ้าหน้าที่"
        )
        reply_done(event.reply_token, result)
        reset(uid)
        return

# -------------------- คำถาม --------------------
def ask_q1(token):
    line_bot_api.reply_message(token, TextSendMessage(
        "Q1: ผลงานของท่านเป็นเรื่องหลักด้านใดมากที่สุด?",
        quick_reply=qr([
            ("การให้บริการประชาชน",                "A1"),
            ("การมีส่วนร่วมประชาชน / เครือข่าย",   "A2"),
            ("ยกระดับระบบบริหาร-จัดการองค์กร (PMQA)","A3"),
            ("อื่น ๆ / ยังไม่แน่ใจ",                  "A0")
        ])
    ))

def ask_q2(token):
    line_bot_api.reply_message(token, TextSendMessage(
        "Q2: ผลงานนำไปใช้จริงแล้วนานเท่าใด?",
        quick_reply=qr([
            ("ยังไม่ถึง 1 ปี", "B0"),
            ("1 – 3 ปี",      "B1"),
            ("3 ปีขึ้นไป",     "B3")
        ])
    ))

# ตัวอย่าง ask_q3 ปรับใหม่
def ask_q3(token):
    line_bot_api.reply_message(
        token,
        TextSendMessage(
            "Q3: จุดเด่นของผลงานตรงกับข้อใดมากที่สุด?",
            quick_reply=qr([
                ("สร้างนวัตกรรมใหม่","C1"),
                ("ต่อยอด/ขยายผล",   "C2"),
                ("บูรณาการดิจิทัล",  "C3"),
                ("แก้ Pain-Point",    "C4"),
                ("เร็ว-ง่าย-โปร่งใส", "C5"),
                ("ผลกระทบชาติ",     "C6"),
                ("ให้ ปชช. ร่วมตัดสิน","C7")
            ])
        )
    )

def reply_done(token, msg):
    line_bot_api.reply_message(
        token,
        TextSendMessage(f"ผลการประเมินเบื้องต้น:\n{msg}")
    )

# -------------------- สำหรับรันบน Render --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)