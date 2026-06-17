import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer

from cassandra_client import insert_forex_rate
from main import run_compute_features_logic
from notifications import manager
import email_client

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "100.75.210.119:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "forex-raw")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "fastapi-websocket-group")

async def start_kafka_consumer():
    logger.info("Initializing Kafka Consumer listening to %s on %s...", KAFKA_TOPIC, KAFKA_BOOTSTRAP_SERVERS)
    
    # Wait a bit on startup for network VPN setup
    await asyncio.sleep(5)
    
    retry_interval = 5
    while True:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset="latest"
            )
            
            await consumer.start()
            logger.info("Kafka Consumer started successfully and subscribed to '%s'!", KAFKA_TOPIC)
            
            try:
                async for msg in consumer:
                    payload = msg.value
                    logger.info("Received Kafka message: %s", payload)
                    
                    try:
                        # 1. Parse fields
                        currency_pair = payload.get("currency_pair")
                        ts_str = payload.get("ts")
                        # Handle timestamp string parsing
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            except ValueError:
                                ts = datetime.now(timezone.utc)
                        else:
                            ts = datetime.now(timezone.utc)
                            
                        forex_data = {
                            "currency_pair": currency_pair,
                            "ts": ts,
                            "open": float(payload.get("open", 0.0)),
                            "high": float(payload.get("high", 0.0)),
                            "low": float(payload.get("low", 0.0)),
                            "close": float(payload.get("close", 0.0)),
                            "volume": int(payload.get("volume", 0))
                        }
                        
                        # 2. Insert into Cassandra
                        insert_forex_rate(forex_data)
                        
                        # 3. Broadcast to WebSocket clients
                        # Format timestamp as string for JSON serialization
                        websocket_payload = forex_data.copy()
                        websocket_payload["ts"] = ts.isoformat()
                        await manager.broadcast_forex_update(websocket_payload)
                        
                        # 4. Trigger feature calculation asynchronously in thread pool (non-blocking)
                        asyncio.create_task(asyncio.to_thread(run_compute_features_logic))
                        
                        # 5. IDR Volatility email alert logic
                        if currency_pair.upper() == "IDR":
                            spread = forex_data["high"] - forex_data["low"]
                            volatility = spread / forex_data["close"] if forex_data["close"] else 0.0
                            threshold = float(os.getenv("IDR_VOLATILITY_THRESHOLD", "0.005"))
                            if volatility >= threshold:
                                email_client.send_idr_alert(
                                    currency_pair=currency_pair,
                                    cluster_label=-1,
                                    is_outlier=True,
                                    volatility=volatility,
                                    details={"open": forex_data["open"], "high": forex_data["high"],
                                             "low": forex_data["low"], "close": forex_data["close"],
                                             "volume": forex_data["volume"]},
                                )
                                
                    except Exception as e:
                        logger.error("Error processing Kafka message payload: %s", e)
                        
            finally:
                await consumer.stop()
                
        except Exception as e:
            logger.error("Kafka Consumer connection failed or encountered error: %s. Retrying in %d seconds...", e, retry_interval)
            await asyncio.sleep(retry_interval)
