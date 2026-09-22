FROM dgtlmoon/changedetection.io:latest

# Use changedetection.io's plugin hook to load the local watch-list layout
# stylesheet without copying or modifying its application source.
COPY row_layout_plugin.py /app/changedetectionio/conditions/plugins/aura_row_layout_plugin.py
COPY row-layout.css /app/changedetectionio/conditions/plugins/static/row-layout.css
