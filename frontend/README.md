# Flowcast Transit AI

Flowcast is an interactive predictive public-transit crowding dashboard built for hackathon demonstration. It visualizes metro and bus demand, forecasts crowd pressure, highlights multimodal interchange risks, and provides AI-assisted operational recommendations.

## Features

- Live metro, bus, and combined network modes
- Clickable station and bus-stop intelligence
- Crowd forecasting across multiple time horizons
- Route performance and reliability analytics
- Operational alerts and recommended interventions
- Interactive demand scenario simulator
- Responsive desktop and mobile interface

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:5173`.

## Production build

```bash
npm run build
```

The current interface uses representative demonstration data and is ready to be connected to historical ticketing, AFC, GPS, and real-time vehicle feeds.
