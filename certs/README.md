# Сертификат Минцифры

Сюда нужно положить корневой сертификат **Russian Trusted Root CA**
в формате **PEM** (файл начинается с `-----BEGIN CERTIFICATE-----`).

Без него запросы к GigaChat падают с ошибкой
`CERTIFICATE_VERIFY_FAILED`.

## Как скачать

Официальная документация GigaChat предлагает прямую ссылку на PEM-версию:

```
https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt
```

Скачайте её и сохраните как `certs/russian_trusted_root_ca.cer`
(расширение не важно — важен формат содержимого).

В PowerShell:

```powershell
Invoke-WebRequest `
  -Uri "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt" `
  -OutFile "certs\russian_trusted_root_ca.cer"
```

Или через `curl.exe`:

```powershell
curl.exe -L "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt" -o "certs\russian_trusted_root_ca.cer"
```

Можно также скачать сертификат с портала Госуслуг: https://www.gosuslugi.ru/crt
Но там нужно выбрать именно PEM-версию. Если файл в формате DER
(бинарный), Python не сможет использовать его напрямую.

## Проверка

Первая строка файла должна быть такой:

```
-----BEGIN CERTIFICATE-----
```

Проверить в PowerShell:

```powershell
Get-Content certs\russian_trusted_root_ca.cer -TotalCount 1
```

Сертификат публичный, не является секретом — его можно хранить в Git.
