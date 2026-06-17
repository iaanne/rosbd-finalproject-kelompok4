#!/bin/bash
until curl -s "http://elasticsearch:9200" >/dev/null; do
  echo "Waiting for Elasticsearch..."
  sleep 2
done

curl -X PUT "http://elasticsearch:9200/cluster-logs" -H 'Content-Type: application/json' -d'
{
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "algorithm": { "type": "keyword" },
      "currency_pair": { "type": "keyword" },
      "cluster_label": { "type": "integer" },
      "is_outlier": { "type": "boolean" },
      "features": {
        "properties": {
          "corr_dxy": { "type": "float" },
          "corr_cny": { "type": "float" },
          "volatility": { "type": "float" }
        }
      }
    }
  }
}'
