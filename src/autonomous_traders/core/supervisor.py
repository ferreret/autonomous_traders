import json
from agents import Agent

# En una implementación más grande, esto usaría la misma factoría get_model que los traders
# pero por ahora, podemos usar un modelo potente directamente.
from autonomous_traders.core.traders import get_model

SUPERVISOR_MODEL = "gpt-4o-mini"

def supervisor_instructions() -> str:
    return '''
    Eres un Supervisor de Cumplimiento y Riesgos en una firma de trading. Tu trabajo es revisar las operaciones propuestas por los agentes traders y decidir si se aprueban o se rechazan.

    Tu decisión debe basarse en TRES criterios principales:

    1.  **GESTIÓN DE RIESGO:**
        - **Regla Principal:** Rechaza cualquier operación individual (compra o venta) cuyo valor total exceda el 25% del valor total actual del portafolio del trader.
        - El valor de la operación se calcula como `cantidad * precio_actual_de_la_acción`.
        - El valor del portafolio se encuentra en el reporte de la cuenta del trader.

    2.  **COHERENCIA DE ESTRATEGIA:**
        - Lee la estrategia del trader y la justificación (`rationale`) de la operación propuesta.
        - ¿La justificación es lógica y se alinea con la estrategia declarada del trader?
        - Ejemplo: Si la estrategia de un trader es "inversión en valor a largo plazo", una propuesta para comprar una acción meme altamente volátil con la justificación "parece que va a subir" debe ser rechazada por falta de coherencia. Sé estricto con esto.

    3.  **CONTROL DE SANIDAD:**
        - ¿La propuesta es lógica? ¿Intenta vender más acciones de las que posee? ¿La cantidad es absurdamente grande?
        - ¿El símbolo de la acción parece válido?

    **PROCESO DE DECISIÓN:**
    Para cada operación pendiente, recibirás los detalles de la propuesta, la estrategia del trader y el estado de su cuenta.
    Debes responder con un JSON que contenga tu decisión y la justificación. El formato DEBE ser:
    {
      "decision": "APPROVE" | "REJECT",
      "feedback": "Una explicación clara y concisa de por qué tomaste esta decisión. Si es un rechazo, debe ser constructivo para que el trader aprenda."
    }

    Ejemplo de Rechazo:
    {
      "decision": "REJECT",
      "feedback": "Rechazado por gestión de riesgo. El valor de la operación ($50,000) supera el límite del 25% del valor del portafolio ($150,000)."
    }

    Ejemplo de Aprobación:
    {
      "decision": "APPROVE",
      "feedback": "Aprobado. La operación se alinea con la estrategia de buscar empresas de crecimiento y el riesgo es aceptable."
    }

    Sé metódico y aplica las reglas de forma consistente. Tu objetivo es proteger a la firma de riesgos innecesarios y asegurar que los traders se adhieran a sus mandatos.
    '''

class Supervisor:
    def __init__(self, model_name=SUPERVISOR_MODEL, mcp_servers=None):
        self.agent = Agent(
            name="Supervisor",
            instructions=supervisor_instructions(),
            model=get_model(model_name),
            mcp_servers=mcp_servers or []
        )

    async def decide_on_trade(self, trade_proposal: dict, trader_account: dict, trader_strategy: str, market_price: float) -> dict:
        """
        Usa el agente LLM para decidir si aprueba o rechaza una operación.
        """
        portfolio_value = trader_account.get("total_portfolio_value", 0)
        trade_value = abs(trade_proposal['quantity'] * market_price)

        prompt = f"""
        **Revisión de Operación Pendiente**

        **Detalles de la Propuesta:**
        - Trader: {trade_proposal['trader_name']}
        - Operación: {'COMPRA' if trade_proposal['quantity'] > 0 else 'VENTA'}
        - Símbolo: {trade_proposal['symbol']}
        - Cantidad: {abs(trade_proposal['quantity'])}
        - Justificación del Trader: "{trade_proposal['rationale']}"

        **Datos para el Análisis:**
        - Estrategia del Trader: "{trader_strategy}"
        - Estado Actual de la Cuenta: {json.dumps(trader_account, indent=2)}
        - Valor Total del Portafolio: ${portfolio_value:,.2f}
        - Precio Actual de la Acción ({trade_proposal['symbol']}): ${market_price:,.2f}
        - Valor Estimado de la Operación: ${trade_value:,.2f}

        Por favor, evalúa esta propuesta según tus reglas (Riesgo, Coherencia, Sanidad) y responde EXCLUSIVAMENTE con el objeto JSON de tu decisión.
        """
        
        response_text = await self.agent.get_response(prompt)
        try:
            # El modelo a veces envuelve la respuesta en ```json ... ```, así que lo limpiamos
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3]

            decision = json.loads(response_text)
            return decision
        except (json.JSONDecodeError, IndexError):
            return {
                "decision": "REJECT",
                "feedback": f"Error interno: La respuesta del supervisor no fue un JSON válido. Respuesta recibida: {response_text}"
            }
