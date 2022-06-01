# What is this

This provides an endpoint for [Appelflap](https://github.com/blinkingtwelve/appelflap) clients to POST a package-signing certificate to, and get a deployment-signed version of that certificate in return as the third certificate in a chain. The deployment certificate (second certificate in the chain) is signed by the Appelflap Root CA (first certificate in the chain), which is recognized by Appelflap clients, enabling them to transitively verify signed update bundles created & offered by peers.


# How to set it up
```
git submodule add git@github.com:blinkingtwelve/django-appelflap-PKI appelflap_PKI
```

Install the requirements from this app's requirements.txt .

Add `'appelflap_PKI'` to your `INSTALLED_APPS`.

Add a URL entry for this apps's urls to your site's urlpatterns.
Recommended (because it's where Appelflap will look, by default):

```
url(r"^appelflap_PKI/", include("appelflap_PKI.urls", namespace='appelflap_PKI')),
```

Add something to your settings as follows:
```
APPELFLAP_PKI = dict(
    deployment_cert_path = '/path/to/my_application_id.pem',
    deployment_key_path  = '/path/to/my_application_id.privkey.pem'
    require_permission   = False
)
```

Iff you got the deployment cert signed by your Appelflap Root CA, Django can now sign X.509 certificates that authenticated users with the `appelflap_PKI.sign_appelflap_p2p_packages` permission POST to `/appelflap_PKI/sign-cert` in PEM format. The response will contain their new certificate as the last certificate in a chain.

With `require_permission = False` (the default, if not specified), any authenticated user can acquire certificates. With `require_permission = True`, the `appelflap_PKI.sign_appelflap_p2p_packages` permission needs to be associated with users in order for them to be able to acquire certificates.

You ~~can~~ ~~should~~ *must* sign your production deployment certificate with your Appelflap Root CA. You could use [XCA](https://hohnstaedt.de/xca/) to make such PKI operations deceptively-easy-clicky.
Appelflap will check the certificate distinguished name's CN (CommonName) attribute against its own Android application ID (for instance "org.nontrivialpursuit.appelflap.demo"), and in addition will verify that it is signed by the Appelflap root CA baked into the APK.

Try not to post the private key of the certificate everywhere.

# The PKI structure
There is no "the certificate" for any specific application ID. There can be many. But one root certificate is used to sign them all. That root certificate is baked into Appelflap and this very Django app, and potentially other places — it is not expected to ever change (which is why we need to be careful with it).

We need at least 1 (but potentially more, if desired) certificate per app ID (usually related to Appelflap "product flavours") if that app is expected to make use of Appelflap's cache exchange mechanism.
These certificates may be shared across servers used by that app. There is no relation between these certificates and server hostnames. The relation is between the certificates and Appelflap product flavours. An Appelflap app does not care whether you copy one single certificate to three servers or rotate three certificates through one server. Its certificate verification process is offline. It does not care whether the certificate "still exists" in the sense that if you delete it from all servers (and the XCA database for good measure), it'll continue to accept device certificates signed by that deployment certificate.

The deployment certificates as hosted on the Bero backend servers are in turn used to sign *device certificates*, of which the private key is stored "in Android", and depending on what that Android is running on may be generated inside and stored inside a cryptographic coprocessor, never to leave it. We never see that private key, but ask Android (and by extension, the cryptographic coprocessor) to do signing operations with it, and it'll just give us the signed goods.

If we would have stringent security requirements, we would want to handle the private keys of the root certificate and deployment certificates in a similar way (eg, not handle them at all). But for now we don't and just let the webapp (and by extension anything that can subvert the webapp) read the private key. One step up (delivering lots of extra security for little fuss)  would be to use a signing agent so that the webapp (which has a large, internet-facing attack surface) never needs to (or gets to) see the private key.

So, in a nutshell:

1. One eternal Appelflap root certificate (though we may use a different root certificate for a different and completely disjunct "PKI universe")
2. Many application IDs
3. For each of those, one or more intermediary deployment certificates, signed by the root cert
4. For each application instance, one (or more, over the lifetime of the app, if we delete its cert and let it request a new one) per-device certificate, signed by the intermediary deployment cert
5. For each device certificate, 0..N signed P2P bundles

Or, oversimplified:

1. One root cert
2. Many deployment certs
3. Many many device certs
4. Many many many signed bundles.

