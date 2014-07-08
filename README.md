njt-api
=======

API for finding trains between two connected stops in an agency. (Called "njt-api" from its initial use for New Jersey Transit)

This is an api created with bottle, with the necessary files to run on Google App Engine. It's use is mostly for duckduckgo's instant answer platform. You can find it at [duckduckgo/zeroclickinfo-spice#891](https://github.com/duckduckgo/zeroclickinfo-spice/pull/891)

Usage
=====

0. `git clone`
1. Download the GTFS data for each agency you want to use.
2. Put the zip files in `data/<name>/gtfs.zip`.
3. `pip install --target lib transitfeed bottle` and grab [the GAE stuff](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).
4. You'll need to patch `transitfeed.py`. On linux, this command is `patch lib/transitfeed.py < transitfeed.py.patch`. I would report these errors, but this library hasn't been updated in two years.
5. `python parse.py`

That's it. You can now kick off the GAE instance.

Data Sources
============

+ [Long Island Railroad (lirr)](http://web.mta.info/developers/developer-data-terms.html)
+ [Metro-North (mnr)](http://web.mta.info/developers/developer-data-terms.html)
+ [New Jersey Transit (njt)](https://www.njtransit.com/mt/mt_servlet.srv?hdnPageAction=MTDevLoginTo) - requires account
+ [Port Authority Trans-Hudson (path)](http://www.panynj.gov/path/developers.html)
+ [Washington, D.C. Metro (wmata)](http://www.wmata.com/rider_tools/license_agreement.cfm)
