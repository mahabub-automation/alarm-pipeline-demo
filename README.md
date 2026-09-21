# 🚨 Telecom Alarm Pipeline (Demo)

Sanitized showcase of a production alarm-notification pipeline I built for a 24×7 telecom operations centre. The original processes 10,000+ alarm records every 10 minutes and sends region-wise alerts to 16 operations teams.

> All data here is **synthetic**. No real site IDs, operators, endpoints or company code are included.

## Roadmap

- [x] Synthetic alarm dataset generator (10,000 alarms, 16 regions)
- [ ] Alarm processing with pandas (active alarms, long outages, region summary)
- [ ] Formatted Excel report
- [ ] Region-wise Telegram notifications
- [ ] Scheduled run on GitHub Actions

## Try it

```bash
pip install pandas
python generate_sample_data.py
```

## Author

**Md. Mahabubul Hasan** — [@mahabub-automation](https://github.com/mahabub-automation) · [LinkedIn](https://linkedin.com/in/mahabubulhasan)
