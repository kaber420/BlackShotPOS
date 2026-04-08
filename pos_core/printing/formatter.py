"""
Formateador de tickets ESC/POS para impresoras térmicas.

Genera bytes en formato ESC/POS para:
- format_ticket(): Ticket de venta completo (para el cliente)
- format_comanda(): Comanda de cocina (sin precios, solo items)

Usa la librería python-escpos para construir los comandos.
Referencia: https://python-escpos.readthedocs.io/
"""
from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

from escpos.printer import Dummy  # Dummy = genera bytes sin conectar a hardware

if TYPE_CHECKING:
    from pos_core.sales.models import Order, OrderItem

# ──────────────────────────────────────────────
# Configuración del negocio (leeble desde .env)
# ──────────────────────────────────────────────
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "BLACKSHOT CAFÉ")
BUSINESS_ADDRESS = os.getenv("BUSINESS_ADDRESS", "")
BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "")
BUSINESS_FOOTER = os.getenv("BUSINESS_FOOTER", "¡Gracias por tu visita!")


def _get_printer() -> Dummy:
    """Devuelve una instancia Dummy que captura los bytes ESC/POS."""
    return Dummy()


def _print_header(p: Dummy, title: str) -> None:
    """Imprime el encabezado estándar del negocio."""
    p.set(align="center", bold=True, double_height=True, double_width=True)
    p.text(f"{BUSINESS_NAME}\n")
    p.set(align="center", bold=False, double_height=False, double_width=False)
    if BUSINESS_ADDRESS:
        p.text(f"{BUSINESS_ADDRESS}\n")
    if BUSINESS_PHONE:
        p.text(f"Tel: {BUSINESS_PHONE}\n")
    p.text("-" * 32 + "\n")
    p.set(align="center", bold=True)
    p.text(f"{title}\n")
    p.set(align="left", bold=False)
    p.text("-" * 32 + "\n")


def _print_footer(p: Dummy) -> None:
    """Imprime el pie de página y corta el papel."""
    p.text("-" * 32 + "\n")
    p.set(align="center")
    p.text(f"{BUSINESS_FOOTER}\n")
    p.text(f"{datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
    p.set(align="left")
    p.text("\n\n\n")
    p.cut()


def format_ticket(order: Order) -> bytes:
    """
    Genera el ticket de venta completo para entregar al cliente.
    Incluye: encabezado del negocio, items con precios, total y método de pago.

    Args:
        order: Instancia de Order con items y payments cargados (eager-loaded).

    Returns:
        bytes en formato ESC/POS listos para enviar a la impresora.
    """
    p = _get_printer()

    # ── Encabezado ──────────────────────────────
    _print_header(p, "TICKET DE VENTA")

    # ── Información de la orden ─────────────────
    p.set(bold=False)
    p.text(f"Orden #: {order.id}\n")
    if order.table_id:
        p.text(f"Mesa:    {order.table_id}\n")
    if order.external_reference:
        p.text(f"Ref:     {order.external_reference}\n")
    p.text(f"Tipo:    {order.type}\n")
    p.text("-" * 32 + "\n")

    # ── Items ────────────────────────────────────
    p.set(bold=True)
    p.text(f"{'PRODUCTO':<20}{'PRECIO':>12}\n")
    p.set(bold=False)
    p.text("-" * 32 + "\n")

    total = 0.0
    items: list[OrderItem] = order.items or []

    for item in items:
        product_name = item.product.name if item.product else f"Producto #{item.product_id}"
        # Truncar nombre largo para que quepa en 58mm (32 chars aprox.)
        if len(product_name) > 18:
            product_name = product_name[:17] + "."
        subtotal = item.quantity * item.unit_price
        total += subtotal
        p.text(f"{item.quantity}x {product_name:<18}")
        p.set(align="right")
        p.text(f"${subtotal:.2f}\n")
        p.set(align="left")

        # Modificadores del item
        if item.modifiers:
            for mod in item.modifiers:
                p.text(f"  + {mod.name}\n")

    # ── Total ────────────────────────────────────
    p.text("-" * 32 + "\n")
    p.set(bold=True, double_height=True)
    p.text(f"{'TOTAL':<20}")
    p.set(align="right", double_height=True, bold=True)
    p.text(f"${total:.2f}\n")
    p.set(align="left", bold=False, double_height=False)

    # ── Método de pago ───────────────────────────
    if order.payments:
        p.text("\nPago:\n")
        for payment in order.payments:
            p.text(f"  {payment.method}: ${payment.amount:.2f}\n")

    # ── Footer ───────────────────────────────────
    _print_footer(p)

    return p.output


def format_comanda(order: Order) -> bytes:
    """
    Genera la comanda para la cocina (sin precios).
    Formato grande y legible para ser vista rápidamente en la cocina.

    Args:
        order: Instancia de Order con items cargados.

    Returns:
        bytes en formato ESC/POS.
    """
    p = _get_printer()

    # ── Encabezado compacto ──────────────────────
    p.set(align="center", bold=True, double_height=True, double_width=True)
    p.text("*** COMANDA ***\n")
    p.set(double_height=False, double_width=False)

    p.text(f"ORDEN #{order.id}")
    if order.table_id:
        p.text(f"  |  MESA {order.table_id}")
    p.text("\n")
    p.text(f"{datetime.now().strftime('%H:%M  %d/%m/%Y')}\n")
    if order.external_reference:
        p.text(f"REF: {order.external_reference}\n")

    p.set(align="left", bold=False)
    p.text("=" * 32 + "\n")

    # ── Items ────────────────────────────────────
    items: list[OrderItem] = order.items or []
    for item in items:
        product_name = item.product.name if item.product else f"Producto #{item.product_id}"
        # Nombre grande para legibilidad rápida
        p.set(bold=True, double_height=True)
        p.text(f"{item.quantity}x  {product_name}\n")
        p.set(bold=False, double_height=False)

        # Variant si existe
        if item.variant:
            p.text(f"    [{item.variant.measure}]\n")

        # Modificadores
        if item.modifiers:
            for mod in item.modifiers:
                p.text(f"    + {mod.name}\n")

        p.text("\n")

    p.text("=" * 32 + "\n")
    p.text("\n\n\n")
    p.cut()

    return p.output


def format_ticket_html(order: Order) -> str:
    """
    Genera una página HTML minimalista para imprimir el ticket desde el navegador.
    Incluye estilos CSS para ancho de papel térmico y auto-print.
    """
    items_html = ""
    total = 0.0
    for item in (order.items or []):
        subtotal = item.quantity * item.unit_price
        total += subtotal
        product_name = item.product.name if item.product else f"Producto #{item.product_id}"
        mods_html = "".join([f"<div class='mod'>+ {m.name}</div>" for m in (item.modifiers or [])])
        
        items_html += f"""
        <div class="item">
            <div class="item-main">
                <span>{item.quantity}x {product_name}</span>
                <span>${subtotal:.2f}</span>
            </div>
            {mods_html}
        </div>"""

    payments_html = ""
    if order.payments:
        for p in order.payments:
            payments_html += f"<div class='payment'>{p.method}: ${p.amount:.2f}</div>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Courier New', Courier, monospace; width: 58mm; margin: 0 auto; font-size: 12px; }}
            .center {{ text-align: center; }}
            .header {{ font-size: 16px; font-weight: bold; margin-bottom: 5px; }}
            .divider {{ border-top: 1px dashed #000; margin: 5px 0; }}
            .item-main {{ display: flex; justify-content: space-between; font-weight: bold; }}
            .mod {{ font-size: 10px; margin-left: 10px; }}
            .total {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; margin-top: 10px; }}
            .footer {{ font-size: 10px; color: #555; margin-top: 20px; }}
            @media print {{
                @page {{ margin: 0; }}
                body {{ margin: 5mm; }}
            }}
        </style>
    </head>
    <body>
        <div class="center">
            <div class="header">{BUSINESS_NAME}</div>
            {f"<div>{BUSINESS_ADDRESS}</div>" if BUSINESS_ADDRESS else ""}
            {f"<div>Tel: {BUSINESS_PHONE}</div>" if BUSINESS_PHONE else ""}
            <div class="divider"></div>
            <strong>TICKET DE VENTA</strong>
            <div class="divider"></div>
        </div>
        
        <div>Orden #: {order.id}</div>
        {f"<div>Mesa: {order.table_id}</div>" if order.table_id else ""}
        <div>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
        <div class="divider"></div>
        
        <div class="items">
            {items_html}
        </div>
        
        <div class="divider"></div>
        <div class="total">
            <span>TOTAL:</span>
            <span>${total:.2f}</span>
        </div>

        {f"<div class='payments'><strong>Pagos:</strong>{payments_html}</div>" if payments_html else ""}
        
        <div class="divider"></div>
        <div class="center footer">
            {BUSINESS_FOOTER}<br>
            Blackshot POS v2
        </div>
        
        <script>
            window.onload = () => {{
                window.print();
                // Algunos navegadores cierran la ventana después de imprimir
                setTimeout(() => {{ window.close(); }}, 500);
            }};
        </script>
    </body>
    </html>
    """


def format_comanda_html(order: Order) -> str:
    """Genera el HTML de comanda para cocina (grande, sin precios)."""
    items_html = ""
    for item in (order.items or []):
        product_name = item.product.name if item.product else f"Producto #{item.product_id}"
        variant_html = f"<div>[{item.variant.measure}]</div>" if item.variant else ""
        mods_html = "".join([f"<div>+ {m.name}</div>" for m in (item.modifiers or [])])
        
        items_html += f"""
        <div style="margin-bottom: 15px;">
            <div style="font-size: 1.5em; font-weight: bold;">{item.quantity}x {product_name}</div>
            <div style="font-size: 1em; margin-left:15px;">
                {variant_html}
                {mods_html}
            </div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; width: 58mm; margin: 0 auto; }}
            .center {{ text-align: center; }}
            @media print {{ @page {{ margin: 0; }} body {{ margin: 5mm; }} }}
        </style>
    </head>
    <body>
        <div class="center">
            <h1 style="margin: 5px 0;">COMANDA</h1>
            <div style="font-size: 1.2em;">ORDEN #{order.id}</div>
            {f"<div>MESA {order.table_id}</div>" if order.table_id else "<div>MOSTRADOR</div>"}
            <div style="font-size: 0.8em; margin-bottom: 10px;">{datetime.now().strftime('%H:%M  %d/%m/%Y')}</div>
            <hr>
        </div>
        
        {items_html}
        
        <hr>
        <script>
            window.onload = () => {{
                window.print();
                setTimeout(() => {{ window.close(); }}, 500);
            }};
        </script>
    </body>
    </html>
    """
