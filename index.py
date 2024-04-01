from flask import Flask, render_template, request, g, redirect
import sqlite3
import requests
import math
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('agg')

app = Flask(__name__)
database = 'datafile.db'


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect(database)
    return g.sqlite_db


@app.teardown_appcontext
def close_connection(exception):
    print("我們正在關閉sql connection......")
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    result = cursor.execute("select * from cash")
    cash_result = result.fetchall()
    # calculate taiwanese dollars and us dollars
    taiwanese_dollars = 0
    us_dollars = 0
    for data in cash_result:
        taiwanese_dollars += data[1]
        us_dollars += data[2]
    # get exchange rate
    r = requests.get('https://tw.rter.info/capi.php')
    currency = r.json()
    total = math.floor(taiwanese_dollars + us_dollars *
                       currency['USDTWD']['Exrate'])

    # get all stock info
    result2 = cursor.execute("select * from stock")
    stock_result = result2.fetchall()
    unique_stock_list = []
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])
    # calculate total stock value
    total_stock_value = 0

    # calculate a stock info
    stock_info = []
    for stock in unique_stock_list:
        result = cursor.execute(
            "select * from stock where stock_id = ?", (stock,))
        result = result.fetchall()
        stock_cost = 0      # a stock total cost
        shares = 0          # a stock num
        for d in result:
            shares += d[2]
            stock_cost += d[2] * d[3] + d[4] + d[5]
        # get the current price of stock
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo=" + stock
        response = requests.get(url)
        data = response.json()
        price_array = data['data']
        current_price = float(price_array[len(price_array) - 1][6])

        # a stock total value
        total_value = round(current_price * shares)
        total_stock_value += total_value
        # a stock avg cost
        avg_cost = round(stock_cost/shares, 2)
        # a rate of return
        rate_of_return = round((total_value-stock_cost) * 100/stock_cost, 2)
        stock_info.append({'stock_id': stock, 'stock_cost': stock_cost, 'total_value': total_value,
                          'avg_cost': avg_cost, 'shares': shares, 'current_price': current_price, 'rate_of_return': rate_of_return})

    for stock in stock_info:
        stock['value_percentage'] = round(
            stock['total_value'] * 100/total_stock_value, 2)
    # draw piechart of stock
    if len(unique_stock_list) != 0:
        labels = tuple(unique_stock_list)
        sizes = [d['total_value'] for d in stock_info]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct=None, shadow=None)
        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart.jpg", dpi=200)
    else:
        try:
            os.remove('static/piechart.jpg')
        except:
            pass
    # draw piechart of stock cash
    if us_dollars != 0 or taiwanese_dollars != 0 or total_stock_value != 0:
        labels = ('USD', 'TWD', 'Stock')
        sizes = (us_dollars * currency['USDTWD']['Exrate'],
                 taiwanese_dollars, total_stock_value)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct=None, shadow=None)
        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart2.jpg", dpi=200)
    else:
        try:
            os.remove('static/piechart2.jpg')
        except:
            pass

    data = {'show_pic_1': os.path.exists('static/piechart.jpg'), 'show_pic_2': os.path.exists('static/piechart2.jpg'),
            'total': total, 'currency': currency['USDTWD']
            ['Exrate'], 'ud': us_dollars, 'td': taiwanese_dollars, 'cash_result': cash_result, 'stock_info': stock_info}

    return render_template("index.html", data=data)


@app.route('/cash')
def cash_form():
    return render_template("cash.html")


@app.route('/cash', methods=['POST'])
def submit_cash():
    # get data
    taiwanese_dollars = 0
    us_dollars = 0
    if request.values['taiwanese-dollars'] != "":
        taiwanese_dollars = request.values['taiwanese-dollars']
    if request.values['us-dollars'] != "":
        us_dollars = request.values['us-dollars']
    note = request.values['note']
    date = request.values['date']

    # update db date
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""insert into cash(taiwanese_dollars, us_dollars, note, date_info) values(?,?,?,?)""",
                   (taiwanese_dollars, us_dollars, note, date))
    conn.commit()
    # back to home page
    return redirect("/")


@app.route('/cash-delete', methods=['POST'])
def cash_delete():
    transaction_id = request.values['id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """delete from cash where transaction_id = ?""", (transaction_id))
    conn.commit()
    return redirect("/")


@app.route('/stock')
def stock_form():
    return render_template("stock.html")


@app.route('/stock', methods=['POST'])
def submit_stock():
    # get data
    stock_id = request.values['stock-id']
    stock_num = request.values['stock-num']
    stock_price = request.values['stock-price']
    processing_fee = 0
    tax = 0
    if request.values['processing-fee'] != "":
        processing_fee = request.values['processing-fee']
    if request.values['tax'] != "":
        tax = request.values['tax']
    date = request.values['date']
    # updata db data
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""insert into stock(stock_id,stock_num,stock_price,processing_fee,tax,date_info) values(?,?,?,?,?,?)""",
                   (stock_id, stock_num, stock_price, processing_fee, tax, date))
    conn.commit()
    # back to home page
    return redirect("/")

    return render_template("stock.html")


if __name__ == '__main__':
    app.run(debug=True)
