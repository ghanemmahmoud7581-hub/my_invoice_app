import flet as ft
from datetime import datetime
import random
import platform
import subprocess


# ════════════════════════════════════════════════════════
#  دوال الطباعة الحرارية
# ════════════════════════════════════════════════════════

def reshape_arabic(text: str) -> str:
    """تصحيح شكل الحروف العربية واتجاهها للطابعة الحرارية"""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text


def build_receipt(invoice_no: str, client: str, items: list, date: str) -> str:
    """بناء نص الفاتورة بصيغة ESC/POS نصية"""
    sub = sum(i["qty"] * i["price"] for i in items)
    tax = sub * 0.15
    total = sub + tax

    W = 32  # عرض الطابعة MH-80 = 80mm ≈ 32 حرف

    def center(text): return text.center(W)
    def line(): return "-" * W
    def dline(): return "=" * W
    def row(label, val): return f"{label:<18}{val:>{W - 18}}"

    sections = [
        dline(),
        center(reshape_arabic("فاتورة ضريبية")),
        center(reshape_arabic("غانم سوفت")),
        dline(),
        reshape_arabic(f"رقم الفاتورة : {invoice_no}"),
        reshape_arabic(f"التاريخ      : {date}"),
        reshape_arabic(f"العميل       : {client or 'عميل عام'}"),
        line(),
        reshape_arabic(row("المنتج", "الإجمالي")),
        reshape_arabic(row("الكمية × السعر", "")),
        line(),
    ]

    for item in items:
        t = item["qty"] * item["price"]
        sections.append(reshape_arabic(item["name"][:W]))
        sections.append(
            reshape_arabic(f"  {item['qty']} × {item['price']:.2f}") +
            f"{t:>{W - 16}.2f}"
        )

    sections += [
        line(),
        reshape_arabic(row("المجموع الجزئي", f"{sub:,.2f}")),
        reshape_arabic(row("ضريبة 15%", f"{tax:,.2f}")),
        dline(),
        reshape_arabic(row("الإجمالي", f"{total:,.2f} ر.س")),
        dline(),
        center(reshape_arabic("شكراً لتعاملكم معنا!")),
        center(reshape_arabic("*** غانم سوفت ***")),
        "",
        "",
        "",
    ]

    return "\n".join(sections)


def print_via_intent(receipt_text: str):
    """
    إرسال الفاتورة لتطبيق ESC POS Printer عبر Android Intent
    يعمل فقط على Android — على الكمبيوتر يعرض النص فقط
    """
    if platform.system() == "Linux" and "ANDROID_ROOT" in __import__("os").environ:
        # Android — نستخدم am start لفتح تطبيق ESC POS
        try:
            cmd = [
                "am", "start",
                "-a", "android.intent.action.SEND",
                "-t", "text/plain",
                "--es", "android.intent.extra.TEXT", receipt_text,
                "-p", "com.erchannel.escposprinter",  # package تطبيق ESC POS Printer
            ]
            subprocess.Popen(cmd)
            return True, "تم إرسال الفاتورة للطابعة ✅"
        except Exception as ex:
            return False, f"خطأ: {ex}"
    else:
        # كمبيوتر — معاينة نصية فقط
        return None, receipt_text


# ════════════════════════════════════════════════════════
#  واجهة Flet
# ════════════════════════════════════════════════════════

def main(page: ft.Page):
    page.title = "نظام الفواتير"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F0F4F8"
    page.padding = 0
    page.fonts = {
        "Cairo": "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvalIvTp0iZg.woff2"
    }
    page.theme = ft.Theme(font_family="Cairo")

    # ── الحالة ───────────────────────────────────────────
    invoice_items: list[dict] = []
    invoice_counter = [random.randint(1000, 9999)]

    # ── دوال مساعدة ──────────────────────────────────────
    def calc_totals():
        sub = sum(i["qty"] * i["price"] for i in invoice_items)
        tax = sub * 0.15
        return sub, tax, sub + tax

    def show_snack(msg: str, color: str = "#10B981"):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, text_align=ft.TextAlign.CENTER, color="#FFFFFF"),
            bgcolor=color,
        )
        page.snack_bar.open = True
        page.update()

    def refresh_table():
        rows = []
        for idx, item in enumerate(invoice_items):
            total = item["qty"] * item["price"]
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(idx + 1), text_align=ft.TextAlign.CENTER)),
                    ft.DataCell(ft.Text(item["name"])),
                    ft.DataCell(ft.Text(str(item["qty"]), text_align=ft.TextAlign.CENTER)),
                    ft.DataCell(ft.Text(f'{item["price"]:,.2f}', text_align=ft.TextAlign.CENTER)),
                    ft.DataCell(ft.Text(f'{total:,.2f}', text_align=ft.TextAlign.CENTER,
                                        weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="#EF4444",
                        tooltip="حذف",
                        on_click=lambda e, i=idx: delete_item(i),
                    )),
                ])
            )
        items_table.rows = rows
        sub, tax, total = calc_totals()
        subtotal_text.value = f"{sub:,.2f} ر.س"
        tax_text.value     = f"{tax:,.2f} ر.س"
        total_text.value   = f"{total:,.2f} ر.س"
        page.update()

    def delete_item(idx):
        invoice_items.pop(idx)
        refresh_table()

    def add_item(e):
        name      = field_name.value.strip()
        qty_str   = field_qty.value.strip()
        price_str = field_price.value.strip()
        error = False

        if not name:
            field_name.error_text = "أدخل اسم المنتج"
            error = True
        else:
            field_name.error_text = None

        try:
            qty = int(qty_str)
            if qty <= 0: raise ValueError
            field_qty.error_text = None
        except ValueError:
            field_qty.error_text = "كمية غير صحيحة"
            error = True

        try:
            price = float(price_str)
            if price < 0: raise ValueError
            field_price.error_text = None
        except ValueError:
            field_price.error_text = "سعر غير صحيح"
            error = True

        if error:
            page.update()
            return

        invoice_items.append({"name": name, "qty": qty, "price": price})
        field_name.value = field_qty.value = field_price.value = ""
        field_name.focus()
        refresh_table()

    def clear_invoice(e):
        invoice_items.clear()
        invoice_counter[0] = random.randint(1000, 9999)
        invoice_number.value = f"#{invoice_counter[0]}"
        refresh_table()

    # ── طباعة حرارية ────────────────────────────────────
    def do_print(e):
        if not invoice_items:
            show_snack("لا توجد منتجات في الفاتورة!", "#EF4444")
            return

        receipt = build_receipt(
            invoice_no=str(invoice_counter[0]),
            client=field_client.value,
            items=invoice_items,
            date=datetime.now().strftime("%Y-%m-%d"),
        )

        ok, msg = print_via_intent(receipt)

        if ok is None:
            # كمبيوتر — اعرض المعاينة النصية
            preview_text.value = msg
            preview_dialog.open = True
            page.update()
        elif ok:
            show_snack(msg, "#10B981")
        else:
            show_snack(msg, "#EF4444")

    # ── حوار المعاينة (للكمبيوتر فقط) ───────────────────
    preview_text = ft.Text(
        "",
        font_family="monospace",
        size=13,
        selectable=True,
        color="#1E293B",
    )
    preview_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("معاينة الفاتورة", weight=ft.FontWeight.BOLD,
                      text_align=ft.TextAlign.CENTER),
        content=ft.Container(
            content=ft.Column([preview_text], scroll=ft.ScrollMode.AUTO),
            width=400, height=420,
            bgcolor="#F8FAFC",
            border_radius=8,
            padding=16,
        ),
        actions=[
            ft.TextButton(
                "إغلاق",
                on_click=lambda e: setattr(preview_dialog, "open", False) or page.update(),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.overlay.append(preview_dialog)

    # ════════════════════════════════════════════════════
    #  مكونات الواجهة
    # ════════════════════════════════════════════════════

    invoice_number = ft.Text(
        f"#{invoice_counter[0]}", size=14,
        color="#64748B", weight=ft.FontWeight.W_500,
    )

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.RECEIPT_LONG, color="#3B82F6", size=28),
                ft.Text("نظام الفواتير", size=22,
                        weight=ft.FontWeight.BOLD, color="#1E293B"),
            ], spacing=10),
            ft.Column([
                ft.Text("رقم الفاتورة", size=11, color="#94A3B8"),
                invoice_number,
            ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor="#FFFFFF",
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
        shadow=ft.BoxShadow(blur_radius=8, color="#1E293B18", offset=ft.Offset(0, 2)),
    )

    # بيانات العميل
    field_client = ft.TextField(
        label="اسم العميل",
        hint_text="أدخل اسم العميل...",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=10, filled=True,
        fill_color="#FFFFFF",
        border_color="#E2E8F0",
        focused_border_color="#3B82F6",
        expand=True,
    )

    client_card = ft.Container(
        content=ft.Column([
            ft.Text("بيانات العميل", size=14,
                    weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Row([
                field_client,
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color="#64748B"),
                        ft.Text(datetime.now().strftime("%Y/%m/%d"),
                                size=14, color="#475569",
                                weight=ft.FontWeight.W_500),
                    ], spacing=6),
                    bgcolor="#F1F5F9", border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=18),
                ),
            ], spacing=12),
        ], spacing=12),
        bgcolor="#FFFFFF", border_radius=14, padding=20,
        shadow=ft.BoxShadow(blur_radius=6, color="#1E293B10", offset=ft.Offset(0, 2)),
    )

    # حقول المنتج
    field_name = ft.TextField(
        label="اسم المنتج / الخدمة", hint_text="مثال: استشارة",
        border_radius=10, filled=True, fill_color="#FFFFFF",
        border_color="#E2E8F0", focused_border_color="#3B82F6",
        expand=2, on_submit=add_item,
    )
    field_qty = ft.TextField(
        label="الكمية", hint_text="1",
        border_radius=10, filled=True, fill_color="#FFFFFF",
        border_color="#E2E8F0", focused_border_color="#3B82F6",
        expand=1, keyboard_type=ft.KeyboardType.NUMBER, on_submit=add_item,
    )
    field_price = ft.TextField(
        label="السعر (ر.س)", hint_text="0.00",
        border_radius=10, filled=True, fill_color="#FFFFFF",
        border_color="#E2E8F0", focused_border_color="#3B82F6",
        expand=1, keyboard_type=ft.KeyboardType.NUMBER, on_submit=add_item,
    )

    add_card = ft.Container(
        content=ft.Column([
            ft.Text("إضافة منتج / خدمة", size=14,
                    weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Row([field_name, field_qty, field_price], spacing=12),
            ft.ElevatedButton(
                "إضافة للفاتورة",
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                on_click=add_item,
                style=ft.ButtonStyle(
                    bgcolor="#3B82F6", color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.padding.symmetric(horizontal=24, vertical=14),
                ),
            ),
        ], spacing=14),
        bgcolor="#FFFFFF", border_radius=14, padding=20,
        shadow=ft.BoxShadow(blur_radius=6, color="#1E293B10", offset=ft.Offset(0, 2)),
    )

    # جدول المنتجات
    items_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("المنتج / الخدمة", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("الكمية", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("السعر", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("الإجمالي", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("حذف", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=10,
        vertical_lines=ft.BorderSide(1, "#F1F5F9"),
        horizontal_lines=ft.BorderSide(1, "#F1F5F9"),
        heading_row_color="#F8FAFC",
        heading_row_height=48,
        data_row_min_height=52,
        column_spacing=20,
        expand=True,
    )

    table_card = ft.Container(
        content=ft.Column([
            ft.Text("المنتجات والخدمات", size=14,
                    weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Container(
                content=ft.Row([items_table], scroll=ft.ScrollMode.AUTO),
                border_radius=10,
            ),
        ], spacing=14),
        bgcolor="#FFFFFF", border_radius=14, padding=20,
        shadow=ft.BoxShadow(blur_radius=6, color="#1E293B10", offset=ft.Offset(0, 2)),
    )

    # الإجماليات
    subtotal_text = ft.Text("0.00 ر.س", size=15, color="#475569", weight=ft.FontWeight.W_500)
    tax_text      = ft.Text("0.00 ر.س", size=15, color="#F59E0B", weight=ft.FontWeight.W_500)
    total_text    = ft.Text("0.00 ر.س", size=20, color="#3B82F6", weight=ft.FontWeight.BOLD)

    def summary_row(label, widget, bold=False):
        return ft.Row([
            ft.Text(label,
                    size=15 if not bold else 17,
                    color="#64748B" if not bold else "#1E293B",
                    weight=ft.FontWeight.W_500 if not bold else ft.FontWeight.BOLD),
            widget,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    totals_card = ft.Container(
        content=ft.Column([
            ft.Text("ملخص الفاتورة", size=14, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Divider(color="#F1F5F9", height=1),
            summary_row("المجموع الجزئي", subtotal_text),
            summary_row("ضريبة القيمة المضافة (15%)", tax_text),
            ft.Divider(color="#E2E8F0"),
            summary_row("الإجمالي النهائي", total_text, bold=True),
        ], spacing=14),
        bgcolor="#FFFFFF", border_radius=14, padding=20,
        shadow=ft.BoxShadow(blur_radius=6, color="#1E293B10", offset=ft.Offset(0, 2)),
    )

    # أزرار الإجراءات
    actions_row = ft.Row([
        ft.OutlinedButton(
            "فاتورة جديدة",
            icon=ft.Icons.ADD,
            on_click=clear_invoice,
            style=ft.ButtonStyle(
                color="#64748B",
                side=ft.BorderSide(1.5, "#CBD5E1"),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=20, vertical=14),
            ),
        ),
        ft.ElevatedButton(
            "طباعة حرارية 🖨️",
            icon=ft.Icons.PRINT,
            on_click=do_print,
            style=ft.ButtonStyle(
                bgcolor="#10B981",
                color="#FFFFFF",
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=24, vertical=14),
            ),
        ),
    ], alignment=ft.MainAxisAlignment.END, spacing=12)

    # ملاحظة الطباعة
    print_note = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, color="#3B82F6", size=16),
            ft.Text(
                "الطباعة تعمل عبر تطبيق ESC POS Printer على Android عبر Bluetooth",
                size=12, color="#64748B",
            ),
        ], spacing=8),
        bgcolor="#EFF6FF",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border=ft.border.all(1, "#BFDBFE"),
    )

    # التخطيط الكامل
    content = ft.Column([
        client_card,
        add_card,
        table_card,
        totals_card,
        print_note,
        actions_row,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    page.add(ft.Column([
        header,
        ft.Container(content=content, padding=ft.padding.all(20), expand=True),
    ], spacing=0, expand=True))


ft.app(target=main)