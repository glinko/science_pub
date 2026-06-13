# Phase 00 Decision

## Цель

Вывести проект из перегруженного `rndocker` в отдельную VM `sci_docker`.

## Выбор

- отдельная VM на Proxmox вместо совместного Docker host;
- Ubuntu 24.04 cloud image;
- provisioning через Proxmox API и MikroTik DHCP reservation.

## Проверка

- VM создаётся на node `pve`;
- получает фиксированный LAN IP;
- принимает SSH под `alex`.

