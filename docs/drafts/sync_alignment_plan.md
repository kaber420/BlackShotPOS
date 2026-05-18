# Sync Alignment and Intelligent Fallbacks

This plan addresses the alignment of sales sync payloads between the POS and Central Core, prevents double-counting on partial payments, and implements an intelligent branch name fallback using the POS local settings.

## Architecture & Decoupling Principle

To prevent architectural coupling, **POS Core (Ventas) remains completely decoupled from configuration and identity**. 

The **Sync Agent (`bs_sync`)** is the sole subsystem responsible for retrieving the node's local configuration, reading pending events from the SQLite outbox queue, wrapping them dynamically with identity metrics (`branch_id`, `branch_name`), and publishing them safely over NATS to the Central Core.

---

## User Review Required

> [!IMPORTANT]
> **Zero POS Core Coupling**: No changes will be made to `pos_core/sales/payment_service.py` regarding configurations. It continues to emit pure transactional data.
> **Sync Agent Enrichment**: In `bs_sync/agent.py`, we will modify the queue-draining mechanism to dynamically inject the local `"branch_name"` into the event payload dictionary immediately before NATS transmission.
> **Central Fallback Processing**: If a sale is received from a branch that hasn't been registered in the Central database yet, the consumer will fall back to using the `"branch_name"` sent by the POS instead of showing `"Sucursal Desconocida"`.

---

## Proposed Changes

### [Sync Agent]

#### [MODIFY] [bs_sync/agent.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_sync/agent.py)
- Update `get_config(session)` to return the branch name:
  ```python
  return settings.nats_url, settings.branch_id, settings.name
  ```
- In `drain_queue(js)`, parse the JSON payload on the fly, inject `"branch_name"`, and serialize it before publishing to NATS:
  ```python
  payload_data = json.loads(event.payload)
  payload_data["branch_name"] = current_branch_name
  payload_str = json.dumps(payload_data)
  ```

---

### [Central Core]

#### [MODIFY] [central_core/event_consumer.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/central_core/event_consumer.py)
- Update `process_payment()` to resolve the `branch_name` with the payload's value as a fallback:
  ```python
  branch_name = branch.name if branch else (data.get('branch_name') or "Sucursal Desconocida")
  ```

---

## Verification Plan

### Payload & Fallback Verification
- Run the NATS consumer and sync agent locally.
- Emit a payment locally in the POS.
- Verify the central consumer logs process the payment with the real branch name retrieved from the POS local settings.
