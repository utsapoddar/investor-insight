"""Join trade events with news headlines to build enriched records for summarization."""


def enrich(
    form4_trades: list[dict],
    thirteenf_results: list[dict],
    crypto_deltas: list[dict],
    news_by_entity: dict[str, list[dict]],
) -> dict:
    enriched_trades = []
    for trade in form4_trades:
        entity = trade["entity"]
        trade["related_news"] = news_by_entity.get(entity, [])[:3]
        enriched_trades.append(trade)

    enriched_13f = []
    for result in thirteenf_results:
        entity = result.get("entity", "")
        result["related_news"] = news_by_entity.get(entity, [])[:3]
        enriched_13f.append(result)

    enriched_crypto = []
    for delta in crypto_deltas:
        entity = delta["entity"]
        delta["related_news"] = news_by_entity.get(entity, [])[:3]
        enriched_crypto.append(delta)

    return {
        "trades": enriched_trades,
        "institutional": enriched_13f,
        "crypto": enriched_crypto,
        "news": news_by_entity,
    }
