import json

with open('routes') as f:
	routes = json.load(f)
with open('stops') as f:
	stops = json.load(f)
with open('dates') as f:
	dates = json.load(f)
with open('dv') as f:
	departurevision = json.load(f)

station_replacements = {
	"princeton junction": "PRINCETON JCT.",
	"philadelphia": "30TH ST. PHL.",
	"montclair state university": "MSU",
	"montclair state": "MSU",
	"jersey ave": "JERSEY AVE."
}
