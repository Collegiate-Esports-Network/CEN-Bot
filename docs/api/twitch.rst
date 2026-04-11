Twitch
======

Twitch live-stream alerts. Polls subscribed channels every 3 minutes using
the Twitch Helix API (Client Credentials OAuth2). Batches up to 100 channel
IDs per request and fires an alert only on an ``is_live`` false → true
state transition.

.. automodule:: cogs.twitch
   :members:
   :show-inheritance:
   :special-members: __init__
