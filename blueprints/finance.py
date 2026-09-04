from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from core.db import get_db_connection, now_local

finance_bp = Blueprint('finance', __name__)

@finance_bp.route('/dicom')
@login_required
def dicom():
    with get_db_connection() as conn:
        debtors = conn.execute('''SELECT d.id, d.name, d.contact_info, 
                                  COALESCE(SUM(t.total - t.amount_paid), 0) as total_balance
                                  FROM debtors d
                                  LEFT JOIN debtor_tickets t ON d.id = t.debtor_id
                                  GROUP BY d.id
                                  ORDER BY total_balance DESC''').fetchall()
    return render_template('dicom.html', active_page='dicom', user=current_user, debtors=debtors)

@finance_bp.route('/api/dicom/debtor/<int:debtor_id>', methods=['GET'])
@login_required
def get_debtor_details(debtor_id):
    with get_db_connection() as conn:
        # Get tickets with their remaining balance
        tickets = conn.execute('''SELECT id, date, total, amount_paid, status,
                                  total - amount_paid as remaining
                                  FROM debtor_tickets 
                                  WHERE debtor_id = ?
                                  ORDER BY date DESC''', (debtor_id,)).fetchall()
        
        # Get items for each ticket
        result = []
        for t in tickets:
            items = conn.execute('''SELECT id, barcode, name, price, quantity, subtotal 
                                    FROM debtor_ticket_items 
                                    WHERE ticket_id = ?''', (t[0],)).fetchall()
            result.append({
                "id": t[0],
                "date": t[1],
                "total": t[2],
                "amount_paid": t[3],
                "status": t[4],
                "remaining": t[5],
                "items": [{"id": i[0], "barcode": i[1], "name": i[2], "price": i[3], "qty": i[4], "subtotal": i[5]} for i in items]
            })
    
    return jsonify(result)

@finance_bp.route('/api/dicom/debtor/<int:debtor_id>/pay', methods=['POST'])
@login_required
def pay_debtor_ticket(debtor_id):
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    amount = float(data.get('amount', 0))
    
    if not ticket_id or amount <= 0:
        return jsonify({"error": "Monto inválido"}), 400
    
    with get_db_connection() as conn:
        conn.execute('''UPDATE debtor_tickets 
                       SET amount_paid = amount_paid + ?,
                           status = CASE WHEN (total - amount_paid - ?) <= 0 THEN 'paid' ELSE 'partial' END
                       WHERE id = ?''', (amount, amount, ticket_id))
        
        # Update status based on final values
        conn.execute('''UPDATE debtor_tickets 
                       SET status = CASE 
                           WHEN total - amount_paid <= 0 THEN 'paid'
                           WHEN amount_paid > 0 THEN 'partial'
                           ELSE 'unpaid'
                       END
                       WHERE id = ?''', (ticket_id,))
        conn.commit()
    
    return jsonify({"status": "success"})

@finance_bp.route('/api/dicom/pay', methods=['POST'])
@login_required
def dicom_pay():
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    amount = float(data.get('amount', 0))
    payment_method = data.get('payment_method', 'efectivo')
    
    if not ticket_id or amount <= 0:
        return jsonify({"error": "Monto inválido"}), 400
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Update the debtor ticket payment
            cur.execute('UPDATE debtor_tickets SET amount_paid = amount_paid + ? WHERE id = ?', (amount, ticket_id))
            
            # Update status based on final values
            cur.execute('''UPDATE debtor_tickets 
                           SET status = CASE 
                               WHEN total - amount_paid <= 0 THEN 'paid'
                               WHEN amount_paid > 0 THEN 'partial'
                               ELSE 'unpaid'
                           END
                           WHERE id = ?''', (ticket_id,))
            
            # Insert into sales table to track daily revenue
            cur.execute('''INSERT INTO sales (date, total, payment_method) 
                           VALUES (?, ?, ?)''', (now_local(), amount, payment_method))
            
            conn.commit()
            
        return jsonify({"status": "success", "amount": amount}), 200
        
    except Exception as e:
        print(f"Dicom Pay Error: {e}")
        return jsonify({"error": str(e)}), 500

@finance_bp.route('/api/dicom/update', methods=['POST'])
@login_required
def update_dicom():
    data = request.get_json()
    name = data.get('name', '').strip()
    amount = float(data.get('amount', 0))
    notes = data.get('notes', '')
    image_url = data.get('image_url', '')
    action = data.get('action')
    
    if not name or amount <= 0:
        return jsonify({"error": "Nombre y monto válidos son requeridos"}), 400
        
    if action == 'add':
        amount = -amount

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO dicom (name, amount, notes, image_url, last_updated) 
                           VALUES (?, ?, ?, ?, ?)
                           ON CONFLICT(name) DO UPDATE SET 
                           amount = amount + excluded.amount,
                           notes = excluded.notes,
                           image_url = CASE WHEN excluded.image_url != "" THEN excluded.image_url ELSE dicom.image_url END,
                           last_updated = excluded.last_updated''', (name, amount, notes, image_url, now_local()))
        conn.commit()
    return jsonify({"status": "success"}), 200

@finance_bp.route('/api/dicom/<int:debtor_id>', methods=['DELETE'])
@login_required
def delete_dicom(debtor_id):
    try:
        with get_db_connection() as conn:
            conn.execute('DELETE FROM dicom WHERE id = ?', (debtor_id,))
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@finance_bp.route('/gastos')
@login_required
def gastos():
    selected_month = request.args.get('month', now_local()[:7])
    selected_day = request.args.get('day', '')
    
    if selected_day:
        day_filter = f"{selected_month}-{selected_day}"
        month_filter = day_filter
    else:
        month_filter = selected_month
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TIMESTAMP DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
                description TEXT NOT NULL,
                amount INTEGER NOT NULL
            )
        ''')
        cur.execute("UPDATE expenses SET date = date || ' 00:00:00' WHERE length(date) = 10 AND date NOT LIKE '% %'")
        conn.commit()
        
        if selected_day:
            sales_total = cur.execute("SELECT SUM(total) FROM sales WHERE date(date) = ?", (day_filter,)).fetchone()[0] or 0
            expenses_total = cur.execute("SELECT SUM(amount) FROM expenses WHERE date(date) = ?", (day_filter,)).fetchone()[0] or 0
            expenses_list = cur.execute("SELECT id, date, description, amount FROM expenses WHERE date(date) = ? ORDER BY date DESC", (day_filter,)).fetchall()
        else:
            sales_total = cur.execute("SELECT SUM(total) FROM sales WHERE substr(date, 1, 7) = ?", (selected_month,)).fetchone()[0] or 0
            expenses_total = cur.execute("SELECT SUM(amount) FROM expenses WHERE substr(date, 1, 7) = ?", (selected_month,)).fetchone()[0] or 0
            expenses_list = cur.execute("SELECT id, date, description, amount FROM expenses WHERE substr(date, 1, 7) = ? ORDER BY date DESC", (selected_month,)).fetchall()
        
    return render_template('gastos.html', 
                           active_page='gastos', 
                           user=current_user,
                           sales_total=sales_total,
                           expenses_total=expenses_total,
                           net_profit=sales_total - expenses_total,
                           expenses=expenses_list,
                           selected_month=selected_month,
                           selected_day=selected_day)

@finance_bp.route('/api/gastos', methods=['POST'])
@login_required
def add_gasto():
    data = request.get_json()
    date = data.get('date', '')
    desc = data.get('description')
    amount = data.get('amount')
    
    if not desc or not amount:
        return jsonify({"error": "Faltan datos"}), 400
        
    with get_db_connection() as conn:
        cur = conn.cursor()
        if date:
            cur.execute("INSERT INTO expenses (date, description, amount) VALUES (?, ?, ?)", (f"{date} {now_local()[11:]}", desc, int(amount)))
        else:
            cur.execute("INSERT INTO expenses (date, description, amount) VALUES (?, ?, ?)", (now_local(), desc, int(amount)))
        conn.commit()
    return jsonify({"success": True})

@finance_bp.route('/api/gastos/<int:gasto_id>', methods=['DELETE'])
@login_required
def delete_gasto(gasto_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = ?", (gasto_id,))
        conn.commit()
    return jsonify({"success": True})

@finance_bp.route('/api/dicom/debtors', methods=['GET'])
@login_required
def get_debtors():
    try:
        with get_db_connection() as conn:
            # Check if table exists
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='debtors'")
            if not cur.fetchone():
                print("Debtors table does not exist!")
                return jsonify([])
            
            cur.execute('SELECT id, name, contact_info FROM debtors ORDER BY name')
            debtors = cur.fetchall()
            print(f"Found {len(debtors)} debtors:", debtors)
            
        return jsonify([{"id": d[0], "name": d[1], "contact_info": d[2]} for d in debtors])
    except Exception as e:
        print(f"Error getting debtors: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@finance_bp.route('/api/dicom/checkout', methods=['POST'])
@login_required
def dicom_checkout():
    try:
        data = request.get_json()
        cart = data.get('cart', [])
        debtor_name = data.get('debtor_name', '').strip()
        contact_info = data.get('contact_info', '').strip()
        initial_payment = data.get('initial_payment', 0) or 0
        initial_method = data.get('initial_method', 'efectivo')
        
        if not cart:
            return jsonify({"error": "Carrito vacío"}), 400
        if not debtor_name:
            return jsonify({"error": "Nombre del deudor requerido"}), 400
        
        total = sum(item.get('subtotal', 0) for item in cart)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Upsert debtor
            cur.execute('''INSERT INTO debtors (name, contact_info) 
                           VALUES (?, ?)
                           ON CONFLICT(name) DO UPDATE SET 
                           contact_info = excluded.contact_info''',
                        (debtor_name, contact_info))
            
            # Get debtor ID
            debtor_id = cur.execute('SELECT id FROM debtors WHERE name = ?', (debtor_name,)).fetchone()[0]
            
            # Insert debtor ticket
            status = 'partial' if initial_payment > 0 else 'unpaid'
            cur.execute('''INSERT INTO debtor_tickets (debtor_id, date, total, amount_paid, status) 
                           VALUES (?, ?, ?, ?, ?)''',
                        (debtor_id, now_local(), total, initial_payment, status))
            ticket_id = cur.lastrowid
            
            # Insert ticket items and deduct stock
            for item in cart:
                cur.execute('''INSERT INTO debtor_ticket_items 
                               (ticket_id, barcode, name, price, quantity, subtotal)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                            (ticket_id, item.get('barcode', ''), item.get('name'), 
                             item.get('price'), item.get('qty'), item.get('subtotal')))
                
                # Deduct stock (skip for manual products)
                if item.get('barcode') and not item.get('barcode', '').startswith(('MANUAL-', 'VARIOS-', 'RAPIDA-')):
                    cur.execute('UPDATE products SET stock = stock - ? WHERE barcode = ?', 
                                (item.get('qty'), item.get('barcode')))
            
            # Record initial payment in sales
            if initial_payment > 0:
                cur.execute('''INSERT INTO sales (date, total, payment_method) 
                               VALUES (?, ?, ?)''', (now_local(), initial_payment, initial_method))
                sale_id = cur.lastrowid
                cur.execute('''INSERT INTO sale_items (sale_id, barcode, name, price, quantity, subtotal)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                            (sale_id, '', 'Abono Dicom', initial_payment, 1, initial_payment))
            
            conn.commit()
            
        return jsonify({"status": "success", "ticket_id": ticket_id, "debtor": debtor_name}), 200
        
    except Exception as e:
        print(f"Dicom Checkout Error: {e}")
        return jsonify({"error": str(e)}), 500

@finance_bp.route('/api/dicom/debtor/<int:debtor_id>', methods=['DELETE'])
@login_required
def delete_debtor(debtor_id):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Delete items first
            cur.execute('DELETE FROM debtor_ticket_items WHERE ticket_id IN (SELECT id FROM debtor_tickets WHERE debtor_id = ?)', (debtor_id,))
            # Delete tickets
            cur.execute('DELETE FROM debtor_tickets WHERE debtor_id = ?', (debtor_id,))
            # Delete debtor
            cur.execute('DELETE FROM debtors WHERE id = ?', (debtor_id,))
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Delete Debtor Error: {e}")
        return jsonify({"error": str(e)}), 500

@finance_bp.route('/api/dicom/ticket/<int:ticket_id>', methods=['DELETE'])
@login_required
def delete_ticket(ticket_id):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Delete items first
            cur.execute('DELETE FROM debtor_ticket_items WHERE ticket_id = ?', (ticket_id,))
            # Delete ticket
            cur.execute('DELETE FROM debtor_tickets WHERE id = ?', (ticket_id,))
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Delete Ticket Error: {e}")
        return jsonify({"error": str(e)}), 500

@finance_bp.route('/api/dicom/item/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Get item info to update ticket total
            item = cur.execute('SELECT ticket_id, subtotal FROM debtor_ticket_items WHERE id = ?', (item_id,)).fetchone()
            if not item:
                return jsonify({"error": "Item no encontrado"}), 404
            
            ticket_id, item_subtotal = item
            
            # Delete item
            cur.execute('DELETE FROM debtor_ticket_items WHERE id = ?', (item_id,))
            
            # Check if ticket has remaining items
            remaining_items = cur.execute('SELECT COUNT(*) FROM debtor_ticket_items WHERE ticket_id = ?', (ticket_id,)).fetchone()[0]
            
            if remaining_items == 0:
                # Delete ticket if no items left
                cur.execute('DELETE FROM debtor_tickets WHERE id = ?', (ticket_id,))
                return jsonify({"status": "success", "ticket_deleted": True}), 200
            
            # Update ticket total
            cur.execute('UPDATE debtor_tickets SET total = total - ? WHERE id = ?', (item_subtotal, ticket_id))
            
            conn.commit()
        return jsonify({"status": "success", "ticket_deleted": False}), 200
    except Exception as e:
        print(f"Delete Item Error: {e}")
        return jsonify({"error": str(e)}), 500

@finance_bp.route('/api/dicom/debtor/<int:debtor_id>/pay-all', methods=['POST'])
@login_required
def pay_all_debtor(debtor_id):
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        payment_method = data.get('payment_method', 'efectivo')
        
        if amount <= 0:
            return jsonify({"error": "Monto inválido"}), 400
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Get all unpaid/partial tickets for this debtor
            tickets = cur.execute('''SELECT id, total, amount_paid, total - amount_paid as remaining 
                                      FROM debtor_tickets 
                                      WHERE debtor_id = ? AND status != 'paid' ''', (debtor_id,)).fetchall()
            
            for ticket in tickets:
                ticket_id = ticket[0]
                remaining = ticket[3]
                
                if remaining > 0:
                    # Pay remaining amount
                    cur.execute('UPDATE debtor_tickets SET amount_paid = amount_paid + ? WHERE id = ?', 
                                (remaining, ticket_id))
                    # Update status
                    cur.execute('''UPDATE debtor_tickets SET status = 'paid' WHERE id = ?''', (ticket_id,))
                    # Record sale
                    cur.execute('''INSERT INTO sales (date, total, payment_method) 
                                   VALUES (?, ?, ?)''', (now_local(), remaining, payment_method))
            
            conn.commit()
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Pay All Debtor Error: {e}")
        return jsonify({"error": str(e)}), 500