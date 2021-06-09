# How to create a self signed certificate on linux

## Example

Requirements:
* openssl

```shell
openssl req -newkey rsa:4096 \
            -x509 \
            -sha256 \
            -days 3650 \
            -nodes \
            -out example.crt \
            -keyout example.key \
            -subj "/C=SI/ST=Ljubljana/L=Ljubljana/O=Security/OU=IT Department/CN=www.example.com"
```

### explanation

* `-newkey rsa:4096` - Creates a new certificate request and 4096 bit RSA key. The default one is 2048 bits.
* `-x509` - Creates a X.509 Certificate.
* `-sha256` - Use 265-bit SHA (Secure Hash Algorithm).
* `-days 3650` - The number of days to certify the certificate for. 3650 is ten years. You can use any positive integer.
* `-nodes` - Creates a key without a passphrase.
* `-out example.crt` - Specifies the filename to write the newly created certificate to. You can specify any file name.
* `-keyout example.key` - Specifies the filename to write the newly created private key to. You can specify any file name.
* `-subj`:
    * `C=` - Country name. The two-letter ISO abbreviation.
    * `ST=` - State or Province name.
    * `L=` - Locality Name. The name of the city where you are located.
    * `O=` - The full name of your organization.
    * `OU=` - Organizational Unit.
    * `CN=` - The fully qualified domain name.

source:
https://linuxize.com/post/creating-a-self-signed-ssl-certificate/#creating-self-signed-ssl-certificate-without-prompt

`CN=` is especially important since it has to match the IP of the server!
The rest of the items in `-subj` are more or less arbitrary.

## What have we actually used for the chat application certificate:

```shell
openssl req -newkey rsa:4096 \
            -x509 \
            -sha256 \
            -days 3650 \
            -nodes \
            -out chatcert.crt \
            -keyout chatcert.key \
            -subj "/C=DE/ST=Berlin/L=Berlin/O=FUB/OU=Rechnersicherheit/CN=localhost"
```
