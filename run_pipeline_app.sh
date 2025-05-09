<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta http-equiv="Content-Style-Type" content="text/css">
  <title></title>
  <meta name="Generator" content="Cocoa HTML Writer">
  <meta name="CocoaVersion" content="2575.5">
  <style type="text/css">
    p.p1 {margin: 0.0px 0.0px 0.0px 0.0px; font: 12.0px Helvetica; -webkit-text-stroke: #000000}
    p.p2 {margin: 0.0px 0.0px 0.0px 0.0px; font: 12.0px Helvetica; -webkit-text-stroke: #000000; min-height: 14.0px}
    span.s1 {font-kerning: none}
  </style>
</head>
<body>
<p class="p1"><span class="s1">#!/usr/bin/env bash</span></p>
<p class="p1"><span class="s1">set -e</span></p>
<p class="p2"><span class="s1"></span><br></p>
<p class="p1"><span class="s1"># 1. Vá para a pasta do seu projeto</span></p>
<p class="p1"><span class="s1">cd ~/Documents/Clari</span></p>
<p class="p2"><span class="s1"></span><br></p>
<p class="p1"><span class="s1"># 2. Ativa seu ambiente</span></p>
<p class="p1"><span class="s1">source ~/clari-venv/bin/activate</span></p>
<p class="p2"><span class="s1"></span><br></p>
<p class="p1"><span class="s1"># 3. Roda o script que baixa os CSVs</span></p>
<p class="p1"><span class="s1">python Captura_reports_Clari.py</span></p>
<p class="p2"><span class="s1"></span><br></p>
<p class="p1"><span class="s1"># 4. Abre o dashboard Streamlit</span></p>
<p class="p1"><span class="s1">streamlit run app.py</span></p>
</body>
</html>
