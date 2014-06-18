njt-api
=======

New Jersey Transit api

This is an api currently set up to run on Google App Engine, though one could easily reconfigure it for a lightweight framework like flask. It's use is mostly for duckduckgo's instant answer platform. You can find it at [duckduckgo/zeroclickinfo-spice#891](https://github.com/duckduckgo/zeroclickinfo-spice/pull/891)

TODO: make it work with other GTFS feeds (namely NYC MTA)

Usage:

0. `git clone`
1. Download the GTFS data from [NJT's site](https://www.njtransit.com/mt/mt_servlet.srv?hdnPageAction=MTDevLoginTo).
2. Put the zip file in the repo root.
3. `(sudo) pip install transitfeed` and grab [the GAE stuff](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).
4. `python parse.py`

That's it. You can now kick off the GAE instance.
