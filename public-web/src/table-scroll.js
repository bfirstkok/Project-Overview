// Keep a native horizontal scrollbar directly above the spreadsheet.
export function connectTableScrollbar(top,viewport){
 const content=top.firstElementChild,table=viewport.querySelector('table');
 const fromTop=()=>{if(Math.abs(viewport.scrollLeft-top.scrollLeft)>1)viewport.scrollLeft=top.scrollLeft;};
 const fromTable=()=>{if(Math.abs(top.scrollLeft-viewport.scrollLeft)>1)top.scrollLeft=viewport.scrollLeft;};
 const resize=()=>{const overflow=!viewport.hidden&&viewport.scrollWidth>viewport.clientWidth+1;top.hidden=!overflow;if(overflow){content.style.width=viewport.scrollWidth+'px';fromTable();}};
 top.addEventListener('scroll',fromTop,{passive:true});viewport.addEventListener('scroll',fromTable,{passive:true});
 const observer=new ResizeObserver(resize);observer.observe(viewport);observer.observe(table);resize();
 return ()=>{observer.disconnect();top.removeEventListener('scroll',fromTop);viewport.removeEventListener('scroll',fromTable);};
}
