import { useEffect, useRef } from 'react';

/** Original OpenDesign deterministic canvas illustration, never patient pixels. */
function drawXray(canvas: HTMLCanvasElement, mode = 'pan', options: { zoom?: number; rotation?: number; slice?: number } = {}){
 const w=1000,h=620;canvas.width=w;canvas.height=h;const c=canvas.getContext('2d');if(!c)return;
 c.fillStyle='#111715';c.fillRect(0,0,w,h);c.save();c.translate(w/2,h/2);c.scale(options.zoom||1,options.zoom||1);c.rotate((options.rotation||0)*Math.PI/180);
 c.globalAlpha=.3;c.strokeStyle='#9da49f';c.lineWidth=16;
 if(mode==='axial'){
  for(let i=0;i<8;i++){c.beginPath();c.ellipse(0,10,240-i*8,205-i*9,0,0,Math.PI*2);c.stroke()}
  for(let i=0;i<14;i++){let a=(i/13)*Math.PI;c.save();c.translate(Math.cos(a)*180,Math.sin(a)*130-70);c.rotate(a);c.fillStyle='#c7cdc5';c.globalAlpha=.6;c.beginPath();c.ellipse(0,0,15,25,0,0,Math.PI*2);c.fill();c.restore()}
 }else{
  c.beginPath();c.ellipse(0,-55,350,185,0,.08,Math.PI-.08);c.stroke();c.beginPath();c.ellipse(0,-40,345,270,0,.04,Math.PI-.04);c.stroke();
  c.lineWidth=4;c.globalAlpha=.15;c.beginPath();c.ellipse(-150,-125,100,80,-.2,0,Math.PI*2);c.stroke();c.beginPath();c.ellipse(150,-125,100,80,.2,0,Math.PI*2);c.stroke();
  for(let row=0;row<2;row++)for(let i=0;i<16;i++){
   const x=(i-7.5)*37,y=(row?45:-18)+Math.pow((i-7.5)/7.5,2)*(row?-50:-35),tilt=(i-7.5)*.035;
   c.save();c.translate(x,y);c.rotate(tilt);if(row)c.scale(1,-1);const width=i<3||i>12?29:23;
   c.globalAlpha=.65;c.fillStyle='#b8c2b8';c.beginPath();c.moveTo(-width/2,25);c.bezierCurveTo(-width,10,-width/2,-4,-width/2,-12);c.bezierCurveTo(-width/2-2,-36,-width/2-5,-70,-7,-83);c.bezierCurveTo(-2,-87,0,-47,0,-32);c.bezierCurveTo(2,-46,2,-85,8,-80);c.bezierCurveTo(width/2+7,-57,width/2,-32,width/2,-12);c.bezierCurveTo(width/2,-2,width,10,width/2,25);c.closePath();c.fill();
   c.globalAlpha=.4;c.strokeStyle='#eef1dc';c.lineWidth=2;c.stroke();c.globalAlpha=.35;c.strokeStyle='#26372f';c.lineWidth=3;c.beginPath();c.moveTo(0,15);c.lineTo(0,-29);c.stroke();c.restore();
  }
 }
 c.restore();
 // Grain is fixed to keep the schematic visually stable while interacting.
 let seed=71;for(let i=0;i<12000;i++){seed=(seed*16807)%2147483647;const x=seed%w;seed=(seed*16807)%2147483647;const y=seed%h;c.fillStyle=`rgba(215,228,216,${.012+(seed%11)/400})`;c.fillRect(x,y,2,2)}
 if(options.slice&&mode!=='pan'){c.strokeStyle='#b4bdb4';c.globalAlpha=.2;c.lineWidth=1;c.beginPath();c.moveTo(w/2,50);c.lineTo(w/2,h-50);c.moveTo(100,h/2+(options.slice-342)/4);c.lineTo(w-100,h/2+(options.slice-342)/4);c.stroke();c.globalAlpha=1}
}

export function DentalSketch() {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => { if (canvas.current) drawXray(canvas.current); }, []);
  return <figure className="dental-sketch"><canvas ref={canvas} className="xray-small" aria-label="Схема челюсти, не снимок пациента" /><figcaption>Схема · не снимок пациента</figcaption></figure>;
}
