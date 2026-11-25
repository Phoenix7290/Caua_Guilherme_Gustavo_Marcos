# Demonstração de Conversa — Agente SupportDesk (3 Turnos)

## Turno 1
**Cliente:** Olá! Meu fone Bluetooth chegou ontem, mas não liga e a luz de carga nem acende.

**Chamadas de ferramenta (`POST /classify`):**
- `tool_call`: `classify_customer_intent({"text":"Olá! Meu fone Bluetooth chegou ontem, mas não liga e a luz de carga nem acende."})`
- `tool_output`: `{"intent": "Billing inquiry", "probability": 0.4949}`

**Agente:** Entendo que você está enfrentando algum problema. Poderia esclarecer se a questão está relacionada a uma cobrança, fatura ou se é um problema técnico com o produto (como não ligar ou a luz de carga não acender)? Isso me ajudará a orientar melhor você.

## Turno 2
**Cliente:** Já testei dois cabos USB-C diferentes e deixei 1 hora na tomada, sem sinal de vida. Quero meu dinheiro de volta.

**Chamadas de ferramenta (`POST /classify`):**
- `tool_call`: `classify_customer_intent({"text":"Já testei dois cabos USB-C diferentes e deixei 1 hora na tomada, sem sinal de vida. Quero meu dinheiro de volta."})`
- `tool_output`: `{"intent": "Cancellation request", "probability": 0.5271}`

**Agente:** Entendo que você está enfrentando um problema com o produto e que deseja reembolso. Para processar sua solicitação de estorno, precisarei do número do pedido para verificar o status e iniciar o procedimento. Você pode compartilhá-lo comigo? Também posso ajudar a verificar se há algum erro técnico no produto, se preferir.

## Turno 3
**Cliente:** Obrigado! Antes de finalizar o reembolso, também notei duas cobranças na minha fatura do cartão. Como verifico isso?

**Chamadas de ferramenta (`POST /classify`):**
- `tool_call`: `classify_customer_intent({"text":"Como verifico isso?"})`
- `tool_output`: `{"intent": "Product inquiry", "probability": 0.2334}`

**Agente:** Você mencionou duas cobranças na fatura — poderia esclarecer se essas cobranças estão relacionadas à compra do produto ou a outra transação? Isso ajuda a identificar melhor a origem do problema. Caso seja sobre o pedido original, preciso do número do pedido para verificar o status e encaminhar o reembolso. Deseja mais detalhes sobre como verificar as cobranças no seu cartão?
