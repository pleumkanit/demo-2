# main.py (LINE Bot SMART Quiz)
import os, json
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, PostbackEvent,
    TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, PostbackAction
)

load_dotenv()
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

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

def qr(btns):
    return QuickReply(items=[QuickReplyButton(action=PostbackAction(label=l, data=d, display_text=l)) for l,d in btns])

user_state = {}
def reset(uid):
    user_state[uid] = {"step":0,"A":None,"B":None,"C":None}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def on_text(event):
    uid = event.source.user_id
    text = event.message.text.strip()
    if text.lower() in ["เริ่ม","เริ่มใหม่","reset"]:
        reset(uid); ask_q1(event.reply_token); return
    if uid not in user_state:
        reset(uid); ask_q1(event.reply_token); return
    line_bot_api.reply_message(event.reply_token,
        TextSendMessage("โปรดเลือกจากปุ่มที่กำหนด หรือพิมพ์ "เริ่ม" เพื่อเริ่มใหม่"))

@handler.add(PostbackEvent)
def on_postback(event):
    uid = event.source.user_id
    data = event.postback.data
    st = user_state.get(uid) or reset(uid)

    if st["step"]==0 and data.startswith("A"):
        st["A"]=data; st["step"]=1
        if data=="A3":
            reply_done(event.reply_token,"PMQA")
            reset(uid); return
        ask_q2(event.reply_token); return

    if st["step"]==1 and data.startswith("B"):
        if data=="B0":
            reply_done(event.reply_token,"ผลงานต้องดำเนินการไม่น้อยกว่า 1 ปี")
            reset(uid); return
        st["B"]=data; st["step"]=2
        ask_q3(event.reply_token); return

    if st["step"]==2 and data.startswith("C"):
        st["C"]=data
        key=(st["A"],st["B"],st["C"])
        result = DECISION.get(key,"ยังไม่พบประเภทที่ตรง โปรดปรึกษาเจ้าหน้าที่")
        reply_done(event.reply_token,result)
        reset(uid); return

def ask_q1(token):
    line_bot_api.reply_message(token, TextSendMessage(
        "Q1: ผลงานของท่านเป็นเรื่องหลักด้านใดมากที่สุด?",
        quick_reply=qr([
            ("การให้บริการประชาชน","A1"),
            ("การมีส่วนร่วมประชาชน / เครือข่าย","A2"),
            ("ยกระดับระบบบริหาร-จัดการองค์กร (PMQA)","A3"),
            ("อื่น ๆ / ยังไม่แน่ใจ","A0")
        ])
    ))

def ask_q2(token):
    line_bot_api.reply_message(token, TextSendMessage(
        "Q2: ผลงานนำไปใช้จริงแล้วนานเท่าใด?",
        quick_reply=qr([
            ("ยังไม่ถึง 1 ปี","B0"),
            ("1 – 3 ปี","B1"),
            ("3 ปีขึ้นไป","B3")
        ])
    ))

def ask_q3(token):
    line_bot_api.reply_message(token, TextSendMessage(
        "Q3: จุดเด่นของผลงานตรงกับข้อใดมากที่สุด?",
        quick_reply=qr([
            ("สร้างนวัตกรรมใหม่ก่อนใคร","C1"),
            ("ต่อยอด/ขยายผลจากรางวัลเดิม","C2"),
            ("บูรณาการข้อมูลดิจิทัลหลายหน่วยงาน","C3"),
            ("แก้ Pain Point / End-to-End Process","C4"),
            ("ลดขั้นตอน เร็วขึ้น ถูกลง โปร่งใส","C5"),
            ("Agenda Impact สูงระดับประเทศ","C6"),
            ("เน้นให้ ปชช. ร่วมตัดสินใจจริงจัง","C7")
        ])
    ))

def reply_done(token,msg):
    line_bot_api.reply_message(token, TextSendMessage(f"ผลการประเมินเบื้องต้น:\n{msg}"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)