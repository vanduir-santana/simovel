#!/bin/bash

ARQ=/home/dbit/.dbit-apps/simovel/install/servico-systemd.ini
DIRSYSTEMD=/etc/systemd/system
SERVICO="dbit-simovel-multi360.service"

echo "Copiar dbit-simovel-multi360.service..."
cp $ARQ $DIRSYSTEMD/$SERVICO

echo "daemon-reload..."
systemctl daemon-reload

echo "Adicionando servico..."
systemctl start $SERVICO
systemctl enable $SERVICO

echo "Pronto!"