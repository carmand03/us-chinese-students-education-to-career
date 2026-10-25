/* Small shared UI helpers, also checked without a browser. */
'use strict';
const CombinedUI=(()=>{
 function tooltip(document,lines){const box=document.createElement('div');box.className='network-tooltip';lines.forEach(line=>{const part=document.createElement('div');part.textContent=String(line);box.appendChild(part);});return box;}
 function paceOptions(running,pace){pace=Math.min(2,Math.max(.25,Number(pace)||1));return {enabled:running,timestep:.5*pace,adaptiveTimestep:false,maxVelocity:35*pace,minVelocity:.05};}
 function applyPhysics(network,running,pace){if(!network)return;network.setOptions({physics:paceOptions(running,pace)});if(running)network.startSimulation();else network.stopSimulation();}
 return {tooltip,paceOptions,applyPhysics};
})();
if(typeof module!=='undefined')module.exports=CombinedUI;
