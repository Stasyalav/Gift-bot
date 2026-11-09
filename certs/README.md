# Сертификат Минцифры

Сюда нужно положить корневой сертификат **Russian Trusted Root CA**
(файл `russian_trusted_root_ca.cer`).

Без него запросы к GigaChat падают с ошибкой
`CERTIFICATE_VERIFY_FAILED`.

Скачать: https://www.gosuslugi.ru/crt

Сертификат публичный, не является секретом — его можно хранить в Git.
