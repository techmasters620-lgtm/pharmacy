import csv
from flask import Response, send_file
import shutil
import os, sqlite3
from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'hospitality-pharmacy-2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Create table if not exists
conn = get_db()
conn.execute('''CREATE TABLE IF NOT EXISTS drugs 
(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dosage TEXT, quantity INTEGER, price REAL, expiry_date TEXT, batch_number TEXT)''')

conn.execute('''CREATE TABLE IF NOT EXISTS sales
(id INTEGER PRIMARY KEY AUTOINCREMENT,
drug_name TEXT,
quantity INTEGER,
total REAL,
patient_name TEXT,
date TEXT)''')
conn.commit()
conn.close()


@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db()
    if search:
        drugs = conn.execute("SELECT * FROM drugs WHERE name LIKE ? OR batch_number LIKE ?", ('%'+search+'%', '%'+search+'%')).fetchall()
    else:
        drugs = conn.execute('SELECT * FROM drugs ORDER BY id DESC').fetchall()
    
    # LOW STOCK ALERT - quantity less than 10
    low_stock = conn.execute('SELECT * FROM drugs WHERE quantity < 10').fetchall()
    low_count = len(low_stock)
    
    # EXPIRY ALERT - expires in next 30 days
    next_month = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    expiring = conn.execute('SELECT * FROM drugs WHERE expiry_date <= ? AND expiry_date >= date("now")', (next_month,)).fetchall()
    
    total_drugs = conn.execute('SELECT COUNT(*) FROM drugs').fetchone()[0]
    conn.close()
    return render_template('index.html', drugs=drugs, search=search, low_stock=low_stock, low_count=low_count, expiring=expiring, total_drugs=total_drugs)

# ADD - Inventory
@app.route('/add', methods=['POST'])
def add_drug():
    conn = get_db()
    conn.execute('INSERT INTO drugs (name, dosage, quantity, price, expiry_date, batch_number) VALUES (?,?,?,?,?,?)',
                 (request.form['name'], request.form['dosage'], request.form['quantity'], request.form['price'], request.form['expiry_date'], request.form['batch_number']))
    conn.commit(); conn.close()
    return redirect('/')

# EDIT
@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit_drug(id):
    conn = get_db()
    if request.method == 'POST':
        conn.execute('UPDATE drugs SET name=?, dosage=?, quantity=?, price=?, expiry_date=?, batch_number=? WHERE id=?',
    (request.form['name'], request.form['dosage'], request.form['quantity'], request.form['price'], request.form['expiry_date'], request.form['batch_number'], id))
    conn.commit(); conn.close()
    return redirect('/')
    drug = conn.execute('SELECT * FROM drugs WHERE id=?', (id,)).fetchone()
    conn.close()
    return render_template('edit.html', drug=drug)

# DELETE
@app.route('/delete/<int:id>')
def delete_drug(id):
    conn = get_db()
    conn.execute('DELETE FROM drugs WHERE id=?', (id,))    
    conn.commit(); conn.close()
    return redirect('/')

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    conn = get_db()
    if request.method == 'POST':
        drug_id = request.form['drug_id']
        qty = int(request.form['quantity'])
        patient = request.form['patient_name']
        drug = conn.execute('SELECT * FROM drugs WHERE id = ?', (drug_id,)).fetchone()
        if not drug:
            conn.close()
            return "Drug not found"
        if drug['quantity'] < qty:
            drugs = conn.execute('SELECT * FROM drugs ORDER BY name').fetchall()
            conn.close()
            return render_template('sell.html', drugs=drugs, error='Not enough stock! Only ' + str(drug['quantity']) + ' left for ' + drug['name'])
        new_qty = drug['quantity'] - qty
        total = qty * drug['price']
        conn.execute('UPDATE drugs SET quantity = ? WHERE id = ?', (new_qty, drug_id))
        conn.execute('INSERT INTO sales (drug_name, quantity, total, patient_name, date) VALUES (?, ?, ?, ?, datetime("now", "localtime"))', (drug['name'], qty, total, patient))
        conn.commit()
        drugs = conn.execute('SELECT * FROM drugs ORDER BY name').fetchall()
        conn.close()
        return render_template('sell.html', drugs=drugs, success='Sold ' + str(qty) + ' x ' + drug['name'] + ' for GHS ' + str(total) + '. Stock left: ' + str(new_qty))
    drugs = conn.execute('SELECT * FROM drugs ORDER BY name').fetchall()
    conn.close()
    return render_template('sell.html', drugs=drugs)

@app.route('/sales')
def sales():
    conn = get_db()
    all_sales = conn.execute('SELECT * FROM sales ORDER BY id DESC').fetchall()
    total = conn.execute('SELECT SUM(total) as total FROM sales').fetchone()
    total_money = total['total'] if total['total'] else 0
    conn.close()
    return render_template('sales.html', sales=all_sales, total=total_money)
import os
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    

    

