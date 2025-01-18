# Tapo Prometheus Exporter

Exports energy consumption data from [Tapo devices like P110](https://amzn.to/3FsCgjn) smart devices to Prometheus, allowing monitoring and visualisation in Grafana.
This is a fork of the original project from [FergusInLondon](https://github.com/FergusInLondon/Tapo-P110-Prometheus-Exporter), that allows support for more than the standard P110. Other countries use different types of sockets, which may render P110 less available in their markets.

DISCLAIMER: This is not guaranteed to work with all devices as the Tapo API may change overtime and by device. This project has been tested with model P125M in January 2025.

![Example Grafana Dashboard](https://i.imgur.com/DxLQgKr.png)

## Startup using docker

Create a [docker-compose.yml](docker-compose.yml)

```yml
version: '3'

services:
  tapo-exporter:
    image: povilasid/tapo-exporter
    volumes:
       - ./tapo.yaml:/app/tapo.yaml:ro
    ports:
      - 9333:9333
    environment:
      - TAPO_EMAIL=YOUR@EMAIL.COM
      - TAPO_PASSWORD=CHANGE_ME
      - PORT=9333 # optional
```
Create tapo.yaml and list P110 ips/names that exporter will be able to reach them.
You can check it in the Tapo App -> the plug -> gear in top right -> "Device info": IP address OR in your router Wifi router DHCP leases) tip: make a lease static
```yml
devices:
  living-room:
    ip_address: "192.168.0.2"
    model: "P125M"
```
Run the exporter
```console
docker compose up -d
```
Add exporter to Prometheus by adding a job (replace 127.0.0.1 with your exporter machine):

```yml
scrape_configs:
  - job_name: 'tapo'
    static_configs:
    - targets: ['127.0.0.1:9333']
      labels:
        machine: 'home'
```
Import Grafana dashboard (JSON) - Energy monitoring-1664376150978.json for latest update, or just import by pasting [id 17104](https://grafana.com/grafana/dashboards/17104-energy-monitoring/)

### Building from srouce
```console
git clone https://github.com/PovilasID/P110-Exporter.git
cd TP110-Exporter
docker build -t p110-exporter .
```
Create tapo.yaml as above
Run the exporter
```console
docker compose up -d
```
Add to Prometheus and import Grafana

## Configuration

Communications are done directly with the Tapo devices, therefore all IP addresses must be provided.

```
devices:
  living-room:
    ip_address: "192.168.0.2"
    model: "P125M"
```

## Importing in Grafana

You can use the Energy monitoring-1664376150978.json file to import your dashboard into Grafana via JSON copy paste.
Make sure to replace, before importing, all occurrences in the file of the %model keyword to your TAPO model.

Example:

Replace %model with P125M

After doing this replacement, your dashboard will be successfully loaded into grafana.

## TODO

- [ ] Migrate from PyP100 to https://github.com/petretiandrea/plugp100 (Current Library is not very well maintained, so there are no updates or long dealays then there are breaking firmware changes)

## Disclaimer
This is meant as an alternative independent way to monitor. However, if you are using home automation Home Assistant has HACS integration that is well maintained and if you finda cheap tastoma hardware it better to use that to avoid breaking changes.
