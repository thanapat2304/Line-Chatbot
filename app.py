from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
import re

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = '#'
LINE_CHANNEL_SECRET = '#'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/")
def index():
    return "LINE Bot is Running!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def get_stock(matno, sales_id=None, month=None):
    mock_data = {
        'Y-127771': {
            'stock_info': [
                ('YASKAWA', 'Y-127771', 'SERVO MOTOR 100W SGMJV-01ADA21', '10.00', 'PCS', '5.00', '2.00', 15000.00, 'WH01', 'A01'),
                ('YASKAWA', 'Y-127771', 'SERVO MOTOR 100W SGMJV-01ADA21', '5.00', 'PCS', '2.00', '1.00', 15000.00, 'WH02', 'B02')
            ],
            'sales_history': {
                '4567': {
                    1: {'sales': 12, 'target': 15},
                    2: {'sales': 8, 'target': 10},
                    7: {'sales': 15, 'target': 15}
                }
            }
        },
        '10313': {
            'stock_info': [
                ('MITSUBISHI', '10313', 'CIRCUIT BREAKER 3P 100AF/100AT', '25.00', 'PCS', '10.00', '5.00', 12000.00, 'WH01', 'E01'),
                ('MITSUBISHI', '10313', 'CIRCUIT BREAKER 3P 100AF/100AT', '15.00', 'PCS', '5.00', '3.00', 12000.00, 'WH02', 'E02')
            ],
            'sales_history': {
                '4567': {
                    1: {'sales': 20, 'target': 25},
                    2: {'sales': 18, 'target': 20},
                    7: {'sales': 22, 'target': 25}
                },
                '4535': {
                    7: {'sales': 15, 'target': 20}
                }
            }
        },
        '4535': {
            'stock_info': [
                ('SCHNEIDER', '4535', 'MAGNETIC CONTACTOR 9A 1NO1NC', '30.00', 'PCS', '8.00', '4.00', 8500.00, 'WH01', 'F01'),
                ('SCHNEIDER', '4535', 'MAGNETIC CONTACTOR 9A 1NO1NC', '20.00', 'PCS', '6.00', '2.00', 8500.00, 'WH02', 'F02')
            ],
            'sales_history': {
                '4567': {
                    7: {'sales': 25, 'target': 30}
                }
            }
        }
    }

    try:
        if matno in mock_data:
            stock_info = mock_data[matno]['stock_info']
            sales_data = None
            
            if sales_id and month:
                sales_history = mock_data[matno]['sales_history']
                if sales_id in sales_history and month in sales_history[sales_id]:
                    sales_data = sales_history[sales_id][month]

            brand, matno, matdesc = stock_info[0][0], stock_info[0][1], stock_info[0][2]
            return brand, matno, matdesc, stock_info, sales_data

        return None

    except Exception as e:
        raise Exception(f"Error with mock data: {str(e)}")

def build_stock_flex_message(matno, matdesc, brand, rows):
    contents = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": f"สินค้า: {matno}",
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": matdesc,
                    "size": "md",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": f"แบรนด์: {brand}",
                    "size": "sm",
                    "color": "#888888",
                    "wrap": True
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "md",
                    "contents": []
                }
            ]
        }
    }

    table_content = contents["body"]["contents"][-1]["contents"]

    header_row = {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type": "text", "text": "Balance", "size": "xs", "weight": "bold", "flex": 2, "wrap": True},
            {"type": "text", "text": "UOM", "size": "xs", "weight": "bold", "flex": 1, "wrap": True},
            {"type": "text", "text": "Price", "size": "xs", "weight": "bold", "flex": 2, "wrap": True},
            {"type": "text", "text": "Warehouse", "size": "xs", "weight": "bold", "flex": 2, "wrap": True},
        ],
        "spacing": "sm",
        "width": "100%"
    }
    table_content.append(header_row)

    for row in rows:
        balance, uom, eta, aep, uprice, whcode, locode = row[3:]
        row_box = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": str(balance), "size": "xs", "flex": 2, "wrap": True},
                {"type": "text", "text": str(uom), "size": "xs", "flex": 1, "wrap": True},
                {"type": "text", "text": str(uprice), "size": "xs", "flex": 2, "wrap": True},
                {"type": "text", "text": str(whcode), "size": "xs", "flex": 2, "wrap": True},
            ],
            "spacing": "sm"
        }
        table_content.append(row_box)

    return FlexSendMessage(alt_text="ข้อมูลสินค้า", contents=contents)

def build_stock_summary_flex_message(matno, matdesc, brand, total_stock, total_eta, total_aep, uom, sales_data=None):
    contents = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "สรุปยอดคงเหลือ",
                            "color": "#ffffff",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": matno,
                            "color": "#ffffff",
                            "size": "xl",
                            "flex": 4,
                            "weight": "bold"
                        }
                    ]
                }
            ],
            "backgroundColor": "#1976D2",
            "paddingAll": "20px",
            "spacing": "md"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": matdesc,
                                    "wrap": True,
                                    "color": "#1976D2",
                                    "size": "md",
                                    "flex": 5,
                                    "weight": "bold"
                                },
                                {
                                    "type": "text",
                                    "text": f"แบรนด์: {brand}",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 1
                                }
                            ]
                        }
                    ]
                },
                {
                    "type": "separator",
                    "margin": "lg"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "คงเหลือทั้งหมด",
                                    "size": "sm",
                                    "color": "#666666"
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"{total_stock:,.2f}",
                                            "size": "xl",
                                            "color": "#2E7D32",
                                            "flex": 0,
                                            "weight": "bold"
                                        },
                                        {
                                            "type": "text",
                                            "text": uom,
                                            "size": "sm",
                                            "color": "#2E7D32",
                                            "flex": 0,
                                            "margin": "sm"
                                        }
                                    ],
                                    "spacing": "sm"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "lg"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "รอส่งมอบ",
                                    "size": "sm",
                                    "color": "#666666"
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"{total_eta:,.2f}",
                                            "size": "xl",
                                            "color": "#FF8F00",
                                            "flex": 0,
                                            "weight": "bold"
                                        },
                                        {
                                            "type": "text",
                                            "text": uom,
                                            "size": "sm",
                                            "color": "#FF8F00",
                                            "flex": 0,
                                            "margin": "sm"
                                        }
                                    ],
                                    "spacing": "sm"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "lg"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "อยู่ระหว่างสั่งซื้อ",
                                    "size": "sm",
                                    "color": "#666666"
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"{total_aep:,.2f}",
                                            "size": "xl",
                                            "color": "#1976D2",
                                            "flex": 0,
                                            "weight": "bold"
                                        },
                                        {
                                            "type": "text",
                                            "text": uom,
                                            "size": "sm",
                                            "color": "#1976D2",
                                            "flex": 0,
                                            "margin": "sm"
                                        }
                                    ],
                                    "spacing": "sm"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "lg"
                        }
                    ],
                    "margin": "lg"
                }
            ]
        }
    }

    if sales_data:
        sales_section = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "separator",
                    "margin": "xxl"
                },
                {
                    "type": "text",
                    "text": "ผลงานการขาย",
                    "size": "sm",
                    "color": "#666666",
                    "margin": "xxl"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ยอดขาย",
                            "size": "sm",
                            "color": "#666666",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": f"{sales_data['sales']:,d}",
                            "size": "sm",
                            "color": "#2E7D32",
                            "flex": 1,
                            "weight": "bold"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "เป้าหมาย",
                            "size": "sm",
                            "color": "#666666",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": f"{sales_data['target']:,d}",
                            "size": "sm",
                            "color": "#1976D2",
                            "flex": 1,
                            "weight": "bold"
                        }
                    ],
                    "margin": "sm"
                }
            ],
            "margin": "lg"
        }
        contents["body"]["contents"].append(sales_section)

    return FlexSendMessage(alt_text=f"สรุปยอดคงเหลือ {matno}", contents=contents)

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_text = event.message.text

    if user_text.startswith("ตรวจ"):
        matno = user_text.replace("ตรวจ", "").strip()
        print(f"ได้รับ Matno: {matno}")

        if re.match(r'^[A-Za-z0-9\-]+$', matno):
            try:
                stock_data = get_stock(matno)
                if stock_data:
                    brand, matno, matdesc, rows, _ = stock_data
                    flex_message = build_stock_flex_message(matno, matdesc, brand, rows)
                    line_bot_api.reply_message(
                        event.reply_token,
                        flex_message
                    )
                    return
                else:
                    reply = "ไม่พบข้อมูลสำหรับรหัสนี้"
            except Exception as e:
                reply = f"เกิดข้อผิดพลาด: {str(e)}"
        else:
            reply = "โปรดพิมพ์รหัสสินค้าให้ถูกต้อง เช่น Y-127771"

    elif user_text.startswith("คงเหลือ"):
        pattern = r'คงเหลือ\s+(\w+(?:-\w+)?)\s+ของ\s+(\d+)\s+เดือน\s+(\d+)'
        match = re.match(pattern, user_text)
        
        if match:
            matno = match.group(1)
            sales_id = match.group(2)
            month = int(match.group(3))
            
            print(f"ได้รับ Matno: {matno}, Sales ID: {sales_id}, Month: {month}")

            try:
                stock_data = get_stock(matno, sales_id, month)
                if stock_data:
                    brand, matno, matdesc, rows, sales_data = stock_data
                    total_stock = sum(float(row[3]) for row in rows)
                    total_eta = sum(float(row[5]) for row in rows)
                    total_aep = sum(float(row[6]) for row in rows)
                    uom = rows[0][4]

                    flex_message = build_stock_summary_flex_message(
                        matno, matdesc, brand,
                        total_stock, total_eta, total_aep, uom,
                        sales_data
                    )
                    line_bot_api.reply_message(
                        event.reply_token,
                        flex_message
                    )
                    return
                else:
                    reply = "ไม่พบข้อมูลสำหรับรหัสนี้"
            except Exception as e:
                reply = f"เกิดข้อผิดพลาด: {str(e)}"
        else:
            reply = "โปรดพิมพ์คำสั่งให้ถูกต้อง เช่น 'คงเหลือ 10313 ของ 4567 เดือน 7'"

    else:
        reply = "โปรดพิมพ์คำสั่งให้ถูกต้อง:\n1. 'ตรวจ' ตามด้วยรหัสสินค้า เช่น 'ตรวจ Y-127771'\n2. 'คงเหลือ [รหัสสินค้า] ของ [รหัสเซล] เดือน [เลขเดือน]' เช่น 'คงเหลือ 10313 ของ 4567 เดือน 7'"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)