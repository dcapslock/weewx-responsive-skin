var reTracInfo      = /NexStorm TRAC Report generated ([0-9]{1,}.[0-9]{1,}.[0-9]{1,}) ([0-9]{1,}:[0-9]{1,}:[0-9]{1,})/
var reTracNumStorms = /Tracking ([0-9]{1,}) thunderstorms/
var reTracStorms    = /^-----.*$(\r\n)(.*\r\n){20}^-----.*$\r\n/gm
var reStormIDTime   = /ID.([A-Za-z0-9-]+).detected.([0-9]+:[0-9]+)/
var reStormBearDist = /bearing.([0-9]+[\.]?[0-9]?).dgr.distance.([0-9]+).km/
var reStormLastAct  = /Last recorded activity\s+([0-9]+:[0-9]+)/
var reStormIntsCls  = /Intensity.class\s+([A-Za-z]+)/
var reStormIntsTrend= /Intensity.trend\s+([A-Za-z ]+)/
var reStormCurrSR   = /Current.strikerate\s+([0-9]+)\/minute/
var reStormPeakSR   = /Peak.strikerate\s+([0-9]+)\/minute/
var reStormTotStrk  = /Total.recorded.strikes\s+([0-9]+)/
var reStormCGStrk   = /Cloud-Ground.strikes\s+([0-9]+)[ -]+([0-9]+\.[0-9]+)%/
var reStormICStrk   = /Intracloud.strikes\s+([0-9]+)[ -]+([0-9]+\.[0-9]+)%/
var reStormPosCG    = /Positive.Cloud-Ground\s+\[\+CG\]\s+([0-9]+)[ -]+([0-9]+\.[0-9]+)%/
var reStormNegCG    = /Negative.Cloud-Ground\s+\[\-CG\]\s+([0-9]+)[ -]+([0-9]+\.[0-9]+)%/
var reStormPosIC    = /Positive.Intracloud\s+\[\+IC\]\s+([0-9]+)[ -]+([0-9]+\.[0-9]+)%/
var reStormNegIC    = /Negative.Intracloud\s+\[\-IC\]\s+([0-9]+)[ -]+([0-9]+\.[0-9]+)%/

if (!String.prototype.format) {
    String.prototype.format = function () {
        var args = arguments;
        return this.replace(/\{\{|\}\}|\{(\d+)\}/g, function (curlyBrack, index) {
            return ((curlyBrack == "{{") ? "{" : ((curlyBrack == "}}") ? "}" : args[index]));
        });
    };
}

//Compass ordinal point code adapted from
//http://codegolf.stackexchange.com/questions/21927/convert-degrees-to-one-of-the-32-points-of-the-compass
s=String;
s.prototype.r = s.prototype.replace;
function calcCompassPoint(degInput) {
    input = degInput / 11.25;
    var j = ~~(input % 8),
        input = (input / 8)|0 % 4,
        cardinal = ['north', 'east', 'south', 'west'],
        pointDesc = ['1', '1 by 2', '1-C', 'C by 1', 'C', 'C by 2', '2-C', '2 by 1'],
        str1, str2, strC;
 
    str1 = cardinal[input];
    str2 = cardinal[(input + 1) % 4];
    strC = (str1 == cardinal[0] | str1 == cardinal[2]) ? str1 + str2 : str2 + str1;
    return pointDesc[j].r('1', str1).r('2', str2).r('C', strC);
}

function getShortName(name) {
    return name.r(/north/g, "N").r(/east/g, "E").r(/south/g, "S").r(/west/g, "W").r(/by/g, "b").r(/[\s-]/g, "");
}

function getIntensityStr(intensity) {
    return intensity.r(/weak/gi, "+").r(/moderate/gi, "++").r(/strong/gi, "+++").r(/Severe/g, "++++");
}

function getIntensityRowBgColour(intensity) {
    color = intensity.r(/weak/gi, "").r(/moderate/gi, "yellow").r(/strong/gi, "orange").r(/Severe/g, "red");
    return 'bgcolor="{0}"'.format(color);
}

function getTrendStr(trend) {
    return trend.r(/intensifying/gi, '\u25B2').r(/weakening/gi, '\u25BC').r(/no change/gi, '\u25BA');
}

function tracSuccess( data ) {
    var TracInfo, TracNumStorms, TracStorms, StormIDTime, StormBearDist, StormLstAct, StormIntsCls, StormIntsTrnd;
    var StormCurrSR, StormPeakSR, StormTotStrk, StormCGStrk, StormICStrk, StormPosCG, StormNegCG, StormPosIC, StormNegIC;
    var stormData, stormID, tracData = {}, tracStorms = 'TracStorms';

    //If header is not present this wil not match meaning no storms.
    //In this case tracData will be an empty array
    TracInfo = reTracInfo.exec(data);
    if (TracInfo !== null) {
        tracData['ReportDate'] = moment(TracInfo[1], "DD.MM.YYYY");
        tracData['ReportTime'] = moment(TracInfo[2], "HH:mm:ss");

        TracNumStorms = reTracNumStorms.exec(data);
        if (TracNumStorms !== null) {
            tracData['TracNumStorms'] = TracNumStorms[1];
        }

        tracData[tracStorms] = {};

        while ((m = reTracStorms.exec(data)) !== null) {
            // This is necessary to avoid infinite loops with zero-width matches
            if (m.index === reTracStorms.lastIndex) {
                reTracStorms.lastIndex++;
            }

            stormData = m[0];

            StormIDTime = reStormIDTime.exec(stormData);
            if (StormIDTime !== null) {
                stormID = StormIDTime[1];
                tracData[tracStorms][stormID] = [];
                tracData[tracStorms][stormID]['ID'] = stormID;
                tracData[tracStorms][stormID]['Time'] = StormIDTime[2];
            }
            else {
                // Can't find ID so can't set up array. Stop parsing
                break;
            }

            StormBearDist = reStormBearDist.exec(stormData);
            if (StormBearDist !== null) {
                tracData[tracStorms][stormID]['Bearing'] = StormBearDist[1];
                tracData[tracStorms][stormID]['Distance'] = StormBearDist[2];
            }

            StormLastAct = reStormLastAct.exec(stormData);
            if (StormLastAct !== null) {
                tracData[tracStorms][stormID]['LastActivity'] = StormLastAct[1];
            }

            StormIntsCls = reStormIntsCls.exec(stormData);
            if (StormIntsCls !== null) {
                tracData[tracStorms][stormID]['IntensityClass'] = StormIntsCls[1];
            }

            StormIntsTrend = reStormIntsTrend.exec(stormData);
            if (StormIntsTrend !== null) {
                tracData[tracStorms][stormID]['IntensityTrend'] = StormIntsTrend[1];
            }

            StormCurrSR = reStormCurrSR.exec(stormData);
            if (StormCurrSR !== null) {
                tracData[tracStorms][stormID]['CurrentSR'] = StormCurrSR[1];
            }

            StormPeakSR = reStormPeakSR.exec(stormData);
            if (StormPeakSR !== null) {
                tracData[tracStorms][stormID]['PeakSR'] = StormPeakSR[1];
            }
        } 
    }

    return tracData;
}

function trac(tracFile, tracDiv) {
    $.get(tracFile, 
        { t: new Date().getTime() }, 
        function(data) {
        var outputHTML;
        tracData = tracSuccess(data);

        //Update page DIV
        if ('TracNumStorms' in tracData) {
            outputHTML = '<h6><small>StormTRAC report generated at {0} {1}</small></h6>'.format(tracData['ReportTime'].format("hh:mmA"), tracData['ReportDate'].format("ddd D MMM YYYY"));
            outputHTML += '<table class="table table-condensed table-responsive"><tbody>';
            outputHTML += '<tr><td class="text-primary" colspan="6">Tracking {0} thunderstorms</tr>'.format(tracData['TracNumStorms']);
            outputHTML += '<tr><td><strong></strong></td><td><strong>TZero</strong></td><td><strong>Distance</strong></td><td><strong>Bearing</strong></td><td class="text-right"><strong><span class="glyphicon glyphicon-flash"></span>/min</strong></td><td class="text-right"><strong><span class="glyphicon glyphicon-flash"></span><span class="glyphicon glyphicon-cloud"></span></strong></td></tr>';

            var i=1;
            for (var key in tracData['TracStorms']) {
                storm = tracData['TracStorms'][key];
                outputHTML += '<tr {0}><td>{1}</td><td>{2}</td><td>{3} km</td><td>{4}</td><td class="text-right">{5}</td><td class="text-right">{6}</td>'.format(
                                getIntensityRowBgColour(storm['IntensityClass']), i, storm['Time'], storm['Distance'], getShortName(calcCompassPoint(storm['Bearing'])),
                                storm['CurrentSR'], getIntensityStr(storm['IntensityClass']) + getTrendStr(storm['IntensityTrend']));
                i += 1;
            };

            outputHTML += '</tbody></table>';
        }
        else {
            outputHTML = '<table class="table table-condensed table-responsive"><tbody>';
            outputHTML += '<tr><td class="text-primary">No thunderstorms detected</td></tr></tbody></table>';
        }

        $(tracDiv).html(outputHTML);
    });
}
