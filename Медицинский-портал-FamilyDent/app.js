/* FamilyDent portal · shared local prototype state and interactions */
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const params=new URLSearchParams(location.search), page=document.body.dataset.page;
const storage={get(key,fallback){try{return JSON.parse(localStorage.getItem('fd-portal:'+key))??fallback}catch{return fallback}},set(key,value){try{localStorage.setItem('fd-portal:'+key,JSON.stringify(value))}catch{toast('Не удалось сохранить изменения в браузере.')}}};
const initialStudies=[
{id:'FD-260184',name:'Мария Соколова',dob:'14.03.1988',type:'CBCT',title:'КЛКТ обеих челюстей',date:'01.11.2026',time:'09:42',fresh:true},
{id:'FD-260183',name:'Тимур Назаров',dob:'22.08.1992',type:'OPG',title:'Панорамный снимок',date:'01.11.2026',time:'09:15',fresh:true},
{id:'FD-260182',name:'Елена Абдуллоева',dob:'03.12.1979',type:'CBCT',title:'КЛКТ верхней челюсти',date:'31.10.2026',time:'17:30',fresh:true},
{id:'FD-260181',name:'Дмитрий Каримов',dob:'11.06.1985',type:'CBCT',title:'КЛКТ обеих челюстей',date:'31.10.2026',time:'15:50',fresh:false},
{id:'FD-260180',name:'Анна Белова',dob:'27.02.1996',type:'OPG',title:'Панорамный снимок',date:'31.10.2026',time:'14:05',fresh:false},
{id:'FD-260179',name:'Рустам Саидов',dob:'19.09.1972',type:'IO',title:'Прицельный снимок · 3.6',date:'30.10.2026',time:'12:10',fresh:false},
{id:'FD-260178',name:'София Мирзоева',dob:'05.05.2001',type:'CBCT',title:'КЛКТ нижней челюсти',date:'30.10.2026',time:'10:35',fresh:false},
{id:'FD-260177',name:'Павел Волков',dob:'16.01.1990',type:'IO',title:'Прицельный снимок · 1.6',date:'29.10.2026',time:'11:20',fresh:false}
];
let studies=storage.get('studies',initialStudies);
let staff=storage.get('staff',[
{id:'u1',name:'Александр Миронов',email:'a.mironov@example.test',role:'Врач',clinic:'Айни, 45',status:'Активен'},
{id:'u2',name:'Елена Романова',email:'e.romanova@example.test',role:'Сотрудник',clinic:'Айни, 45',status:'Активен'},
{id:'u3',name:'Ирина Лебедева',email:'i.lebedeva@example.test',role:'Администратор',clinic:'Айни, 45',status:'Активен'},
{id:'u4',name:'Денис Фомин',email:'d.fomin@example.test',role:'Врач',clinic:'Филиал «Восток»',status:'Активен'}
]);
let clinics=storage.get('clinics',[{name:'FamilyDent · Айни, 45',address:'Душанбе, ул. Айни, 45',status:'Активна'},{name:'FamilyDent · Восток',address:'Душанбе, ул. Сино, 18',status:'Активна'}]);
let audit=storage.get('audit',[{time:'09:45',actor:'Елена Романова',event:'Назначен врач · FD-260184',detail:'Александр Миронов'},{time:'09:42',actor:'Елена Романова',event:'Добавлено исследование · FD-260184',detail:'Мария Соколова'},{time:'Вчера',actor:'Александр Миронов',event:'Создана ссылка пациенту · FD-260181',detail:'Срок доступа: 7 дней'}]);
function log(event,detail=''){audit.unshift({time:new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}),actor:'Текущий пользователь',event,detail});storage.set('audit',audit)}
function toast(message){const el=$('.toast');el.textContent=message;el.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.hidden=true,5000)}
function modal(title,body){$('#dialog-title').textContent=title;$('#dialog-body').innerHTML=body;$('#dialog').showModal()}
$('[data-close]').onclick=()=>$('#dialog').close();
$('#dialog').addEventListener('click',e=>{if(e.target===$('#dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close()}});
$('[data-menu]')?.addEventListener('click',e=>{const open=$('.sidebar').classList.toggle('mobile-open');e.currentTarget.setAttribute('aria-expanded',open);e.currentTarget.setAttribute('aria-label',open?'Закрыть меню':'Открыть меню')});
$('[data-notifications]')?.addEventListener('click',()=>{modal('Уведомления',`<div class="stack">${audit.slice(0,5).map(e=>`<article><h3>${escapeHTML(e.event)}</h3><p>${escapeHTML(e.detail)} · ${escapeHTML(e.time)}</p></article>`).join('')}</div><p>Настройки уведомлений применяются в разделе «Команда и доступы».</p>`)});
const initials=name=>name.split(' ').slice(0,2).map(x=>x[0]).join('');
/* Doctor workspace: search, status and modality filters, patient history */
if(page==='doctor'){
 let tab='all';
 function renderStudies(){
  const query=$('#patient-search').value.toLocaleLowerCase('ru'),type=$('#modality').value;
  const rows=studies.filter(s=>(s.name+' '+s.id).toLocaleLowerCase('ru').includes(query)&&(type==='all'||s.type===type)&&(tab==='all'||(tab==='new'?s.fresh:!s.fresh)));
  $('#study-rows').innerHTML=rows.map(s=>`<tr data-od-id="study-row-${escapeHTML(s.id.toLowerCase())}"><td><div class="patient-cell"><span class="avatar">${escapeHTML(initials(s.name))}</span><div><a href="#" data-history="${escapeHTML(s.id)}">${escapeHTML(s.name)}</a><small>${escapeHTML(s.dob)} · ${escapeHTML(s.id)}</small></div></div></td><td data-label="Исследование"><span class="modality">${s.type}</span><span style="display:block;margin-top:5px">${escapeHTML(s.title)}</span></td><td data-label="Дата"><span class="mono">${escapeHTML(s.date)}</span><span class="muted" style="display:block;font-size:10px">${escapeHTML(s.time)}</span></td><td data-label="Статус"><span class="badge ${s.fresh?'good':'neutral'}">${s.fresh?'<i class="dot"></i> Новое':'Просмотрено'}</span></td><td data-label="Действие"><a class="open-row" href="study.html?id=${encodeURIComponent(s.id)}" aria-label="Открыть исследование ${escapeHTML(s.name)}">↗</a></td></tr>`).join('');
  $('#no-results').hidden=rows.length>0;$('#result-count').textContent=`Показано ${rows.length} из ${studies.length}`;
  $('#stat-patients').textContent=new Set(studies.map(s=>s.name)).size;$('#stat-studies').textContent=studies.length;$('#stat-new').textContent=studies.filter(s=>s.fresh).length;
  $$('[data-filter-tab] span').forEach((el,i)=>el.textContent=i===0?studies.length:studies.filter(s=>i===1?s.fresh:!s.fresh).length);
  $$('[data-history]').forEach(a=>a.onclick=e=>{e.preventDefault();const s=studies.find(s=>s.id===a.dataset.history);modal('История пациента',`<h3>${escapeHTML(s.name)}</h3><p>Дата рождения: ${escapeHTML(s.dob)}</p>${studies.filter(x=>x.name===s.name).map(x=>`<div class="info-box"><strong>${escapeHTML(x.title)}</strong><p>${escapeHTML(x.date)} · ${escapeHTML(x.id)}</p><a class="btn dark" href="study.html?id=${encodeURIComponent(x.id)}">Открыть исследование ↗</a></div>`).join('')}`)});
 }
 $('#patient-search').addEventListener('input',renderStudies);$('#modality').addEventListener('change',renderStudies);
 $$('[data-filter-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.filterTab;$$('[data-filter-tab]').forEach(x=>x.setAttribute('aria-selected',x===b));renderStudies()});
 const mode=params.get('tab');if(mode){$('#list-title').textContent=mode==='patients'?'Пациенты и история исследований':'Все исследования';$$('.side-nav a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')===`doctor.html?tab=${mode}`))}
 renderStudies();
}
/* Synthetic imaging canvas: explicitly non-diagnostic, deterministic anatomy sketch. */
function drawXray(canvas,mode='pan',options={}){
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
$$('canvas[data-xray]').forEach(c=>drawXray(c,c.dataset.xray));
/* Download requests are deliberately honest: no fake DICOM or Romexis files. */
function downloadDialog(kind){modal('Скачать исследование',`<div class="info-box"><h3>${kind==='romexis'?'DICOM + Romexis Viewer':'Оригинальные файлы DICOM'}</h3><p>FD-260184 · КЛКТ обеих челюстей</p></div><p>Архив снимков пока не подключён. Скачать реальные медицинские файлы и Romexis Viewer можно будет после подключения хранилища клиники.</p><button class="btn dark" id="download-request">Запросить файлы у клиники</button>`);$('#download-request').onclick=()=>{location.href='mailto:support@example.test?subject='+encodeURIComponent('Запрос файлов исследования FD-260184')}}
$$('[data-download]').forEach(b=>b.onclick=()=>downloadDialog(b.dataset.download));
function shareDialog(){
 const existing=storage.get('link',null);const revoked=storage.get('link-revoked',false);
 modal('Доступ к исследованию',`<p>Персональная ссылка для пациента. Она открывает только это исследование.</p><form id="share-form"><label class="field">Email пациента<input type="email" required placeholder="patient@example.test" name="email" value="${escapeHTML(existing?.email||'')}"></label><label class="field">Срок действия<select name="days"><option value="1">24 часа</option><option value="3">3 дня</option><option value="7" selected>7 дней</option></select></label><label class="row small"><input name="notify" type="checkbox" checked> Подготовить уведомление по email</label><p class="small">Ссылка и уведомление будут подготовлены локально. Для защищённой выдачи и отправки письма требуется сервер.</p><button class="btn dark" type="submit">Создать ссылку</button></form><div id="share-result" hidden></div>${existing&&!revoked?'<button class="btn ghost" id="revoke-current" style="margin-top:15px">Отозвать текущую ссылку</button>':''}`);
 $('#revoke-current')?.addEventListener('click',()=>{storage.set('link-revoked',true);log('Отозвана ссылка пациенту','FD-260184');$('#dialog').close();toast('Ссылка отозвана в текущем браузере')});
 $('#share-form').onsubmit=e=>{e.preventDefault();const form=new FormData(e.target);const token=crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2);const link={email:form.get('email'),token,expires:Date.now()+Number(form.get('days'))*86400000,notify:form.get('notify')==='on'};storage.set('link',link);storage.set('link-revoked',false);log('Подготовлена ссылка пациенту',link.email);const url=new URL('patient.html',location.href);url.searchParams.set('token',token);const result=$('#share-result');result.hidden=false;result.innerHTML=`<div class="notice">Локальная ссылка создана до ${new Date(link.expires).toLocaleDateString('ru-RU')}</div><label class="field" style="margin:20px 0">Ссылка<input id="share-url" readonly value="${escapeHTML(url.href)}"></label><button class="btn dark" id="copy-link">Скопировать</button> <a class="btn" href="${escapeHTML(url.href)}">Открыть</a>${link.notify?'<p>Уведомление подготовлено. Отправка писем не подключена.</p>':''}`;e.target.hidden=true;$('#copy-link').onclick=async()=>{try{await navigator.clipboard.writeText(url.href);toast('Ссылка скопирована')}catch{$('#share-url').select();toast('Выделенная ссылка готова для копирования')}}};
}
$$('[data-share]').forEach(b=>b.onclick=shareDialog);
/* Viewer controls: series, slice, zoom, contrast, rotation, pixel measurement. */
if(page==='study'){
 let series='pan',zoom=1,rotation=0,contrast=1,invert=false,measuring=false,points=[];
 const patientMode=params.get('from')==='patient', token=params.get('token');
 const accessLink=storage.get('link',null);
 if(patientMode&&token&&(!accessLink||accessLink.token!==token||Date.now()>accessLink.expires||storage.get('link-revoked',false))){location.replace('patient.html?expired=1');$('.viewer-layout').hidden=true;}
 if(patientMode){const a=$('.viewer-head>a');a.href='patient.html'+(token?'?token='+encodeURIComponent(token):'');a.setAttribute('aria-label','Вернуться к моему исследованию');$('.back-label').textContent='Моё исследование';$('[data-share]').hidden=true}
 const study=studies.find(s=>s.id===params.get('id'))||studies.find(s=>s.id==='FD-260184')||initialStudies[0];
 $('#study-title').textContent=study.name;$('#study-subtitle').textContent=`${study.title} · ${study.date} · ${study.id}`;$('#meta-name').textContent=study.name;$('#meta-dob').textContent=study.dob;$('.viewport-label').firstChild.textContent=study.id;
 // Metadata reflects selected modality; schematic series are only supplied for CBCT.
 const meta=$$('.study-meta .key-value dd');meta[3].textContent=study.title.replace('КЛКТ ','');
 if(study.id!=='FD-260184'){$$('.study-meta>div:last-child .btn').forEach(b=>b.textContent=b.dataset.download==='romexis'?'DICOM + Romexis Viewer':'Файлы DICOM');$$('.study-meta>div:last-child p').forEach((p,i)=>p.textContent=i===0?study.date+', '+study.time+' · Исследование добавлено':'Назначен лечащий врач');}
 if(study.type!=='CBCT'){$$('.series-card').slice(1).forEach(b=>b.hidden=true);$('#slice').disabled=true;$('#slice').value=1;$('#slice-number').textContent='1';$('.viewer-bottom label').innerHTML='Кадр <span class="mono">1 / 1</span>';$('.study-meta .key-value').innerHTML=`<dt>Пациент</dt><dd>${escapeHTML(study.name)}</dd><dt>Дата рождения</dt><dd>${escapeHTML(study.dob)}</dd><dt>Тип</dt><dd>${study.type}</dd><dt>Исследование</dt><dd>${escapeHTML(study.title)}</dd><dt>Архив</dt><dd>Не подключён</dd>`}
 function paint(){drawXray($('#main-xray'),series,{zoom,rotation,slice:Number($('#slice').value)});$('#main-xray').style.filter=`contrast(${contrast}) invert(${invert?1:0})`;$('#zoom-info').textContent=Math.round(zoom*100)+'%';$('#view-info').textContent=`Масштаб ${Math.round(zoom*100)}% · Контраст ${Math.round(contrast*100)}%`;$('#slice-number')&&($('#slice-number').textContent=$('#slice').value);$('#slice').disabled=series==='pan';points=[]}
 $$('[data-series]').forEach(b=>b.onclick=()=>{series=b.dataset.series;$$('[data-series]').forEach(x=>x.classList.toggle('selected',x===b));$('#series-label').textContent={pan:'Панорамная реконструкция',axial:'Аксиальная серия',coronal:'Корональная серия'}[series];paint()});
 $('#slice').addEventListener('input',paint);
 $$('[data-tool]').forEach(b=>b.onclick=()=>{switch(b.dataset.tool){case'zoom':zoom=zoom>=2?1:zoom+.25;break;case'contrast':contrast=contrast>=2?1:contrast+.25;break;case'invert':invert=!invert;b.classList.toggle('active',invert);break;case'rotate':rotation=(rotation+90)%360;break;case'measure':measuring=!measuring;b.classList.toggle('active',measuring);toast(measuring?'Выберите две точки. Расстояние показано в пикселях схемы.':'Измерение выключено');break;case'reset':zoom=contrast=1;rotation=0;invert=measuring=false;$$('[data-tool]').forEach(x=>x.classList.remove('active'));break;case'fullscreen':if(document.fullscreenElement){document.exitFullscreen?.()}else $('#viewport').requestFullscreen?.().catch(()=>toast('Полноэкранный режим недоступен'));break}paint()});
 $('#main-xray').onclick=e=>{if(!measuring)return;const r=e.target.getBoundingClientRect();points.push({x:(e.clientX-r.left)*1000/r.width,y:(e.clientY-r.top)*620/r.height});if(points.length===2){const c=e.target.getContext('2d'),a=points[0],b=points[1];c.strokeStyle='#d8c8a3';c.lineWidth=3;c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.stroke();const d=Math.hypot(b.x-a.x,b.y-a.y);$('#view-info').textContent=`Расстояние: ${Math.round(d/zoom)} px · калибровка DICOM не подключена`;points=[]}};
 paint();if(study.fresh){study.fresh=false;storage.set('studies',studies);log('Открыто исследование',study.id)}
 // Sharing and downloads must refer to the selected study, not a fixed record.
 $$('[data-download]').forEach(b=>b.onclick=()=>{modal('Файлы исследования',`<h3>${escapeHTML(study.title)}</h3><p>${escapeHTML(study.name)} · ${escapeHTML(study.id)}</p><p>Скачивание ${b.dataset.download==='romexis'?'DICOM с Romexis Viewer':'DICOM'} будет доступно после подключения архива клиники. Реальные медицинские файлы в прототипе отсутствуют.</p>`)});
 if(study.id!=='FD-260184')$('[data-share]').onclick=()=>modal('Доступ пациенту',`<p>${escapeHTML(study.name)} · ${escapeHTML(study.id)}</p><p>Выдача защищённой ссылки на это исследование станет доступна после подключения серверного архива.</p>`);
}
/* Patient link lifecycle, including expired/revoked states. */
if(page==='patient'){
 const link=storage.get('link',null), token=params.get('token');const invalid=(token&&(!link||token!==link.token||Date.now()>link.expires||storage.get('link-revoked',false)))||params.get('expired')==='1';
 $('#patient-valid').hidden=!!invalid;$('#patient-expired').hidden=!invalid;
 if(token&&!invalid){$('.access-footer strong').textContent='Ссылка действует до '+new Date(link.expires).toLocaleDateString('ru-RU');$('.patient-preview a').href='study.html?from=patient&token='+encodeURIComponent(token)}
}
/* Email verification UI: no network send and no claim of real authentication. */
if(page==='login'){
 let email='',role='doctor';
 function showEmail(){ $('#auth-content').innerHTML=`<h2>Вход в портал</h2><p class="muted" style="font-size:12px;margin-bottom:28px">Введите рабочий email. Пароль не понадобится.</p><form id="login-form"><label class="field">Электронная почта<input type="email" name="email" placeholder="doctor@example.test" autocomplete="email" required value="${escapeHTML(email)}"></label><label class="field">Рабочее пространство<select name="role"><option value="doctor">Кабинет врача</option><option value="upload">Кабинет сотрудника</option><option value="admin">Кабинет администратора</option></select></label><button class="btn dark" type="submit">Продолжить →</button><p class="small muted">Отправка email и проверка прав доступа требуют подключения сервера.</p></form>`;$('#login-form').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);email=f.get('email');role=f.get('role');showCode()}}
 function showCode(){ $('#auth-content').innerHTML=`<h2>Подтвердите email</h2><p class="muted" style="font-size:12px;margin-bottom:26px">Адрес для входа: <strong>${escapeHTML(email)}</strong></p><form id="code-form"><label class="field">Код подтверждения<input class="code-input" name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required placeholder="000000" aria-describedby="code-help"></label><p class="small muted" id="code-help">Email-сервис ещё не подключён. Для проверки перехода используйте код <span class="mono">246810</span>.</p><p class="error" id="code-error" role="alert" hidden>Код не совпадает. Проверьте шесть цифр.</p><button class="btn dark" type="submit">Войти в кабинет</button><button class="btn ghost" type="button" id="change-email">Изменить email</button></form>`;$('#code-form').onsubmit=e=>{e.preventDefault();if(new FormData(e.target).get('code')!=='246810'){$('#code-error').hidden=false;return}log('Открыто рабочее пространство',email);location.href=role+'.html'};$('#change-email').onclick=showEmail;$('.code-input').focus()}
 showEmail();
}
/* Upload wizard: real local file selection + validation, metadata-only save. */
if(page==='upload'){
 let step=1,files=[],fields={name:'',dob:'',type:'CBCT',title:'КЛКТ обеих челюстей',doctor:'Александр Миронов',clinic:'Айни, 45',notify:true};
 const stage=$('#upload-stage');
 function paintStep(){
  $$('[data-step-label]').forEach(e=>e.classList.toggle('active',Number(e.dataset.stepLabel)===step));$('#upload-back').hidden=step===1;$('#upload-next').textContent=step===3?'Сохранить карточку исследования':'Продолжить →';
  if(step===1){stage.innerHTML=`<h2>Файлы и данные пациента</h2><label class="dropzone" id="dropzone"><span style="font-size:26px">↑</span><strong>Перетащите DICOM или ZIP-архив</strong><p class="muted">Файлы .dcm или .zip · до 2 ГБ каждый</p><input id="dicom-files" type="file" accept=".dcm,.zip" multiple aria-label="Выбрать файлы исследования"></label><div id="file-list" class="stack"></div><div class="two-fields"><label class="field">ФИО пациента<input required name="name" placeholder="Фамилия Имя Отчество" value="${escapeHTML(fields.name)}"></label><label class="field">Дата рождения<input required type="date" name="dob" max="2026-11-01" value="${escapeHTML(fields.dob)}"></label></div><div class="two-fields"><label class="field">Тип исследования<select name="type"><option value="CBCT">КЛКТ (CBCT)</option><option value="OPG">Панорамный снимок (OPG)</option><option value="IO">Прицельный снимок (IO)</option></select></label><label class="field">Название исследования<input required name="title" value="${escapeHTML(fields.title)}"></label></div><p class="error" id="upload-error" role="alert" hidden></p>`;
   $('[name=type]').value=fields.type;$('[name=type]').onchange=e=>{$('[name=title]').value={CBCT:'КЛКТ обеих челюстей',OPG:'Панорамный снимок',IO:'Прицельный снимок'}[e.target.value]};
   function acceptFiles(list){const next=[...list],error=next.find(f=>!(/\.(dcm|zip)$/i.test(f.name))||f.size>2*1024**3||f.size===0);if(error){$('#upload-error').hidden=false;$('#upload-error').textContent='Выберите непустые файлы .dcm или .zip размером до 2 ГБ каждый.';return}files=next;$('#upload-error').hidden=true;showFiles()}
   function showFiles(){$('#file-list').innerHTML=files.map((f,i)=>`<div class="file-entry"><span>${escapeHTML(f.name)}<small class="muted"> · ${(f.size/1024**2).toFixed(1)} МБ</small></span><button type="button" class="icon-btn" data-remove="${i}" aria-label="Удалить файл ${escapeHTML(f.name)}">×</button></div>`).join('');$$('[data-remove]').forEach(b=>b.onclick=()=>{files.splice(Number(b.dataset.remove),1);showFiles()})}
   $('#dicom-files').onchange=e=>acceptFiles(e.target.files);$('#dropzone').ondragover=e=>{e.preventDefault();e.currentTarget.style.borderStyle='solid'};$('#dropzone').ondragleave=e=>e.currentTarget.style.borderStyle='dashed';$('#dropzone').ondrop=e=>{e.preventDefault();e.currentTarget.style.borderStyle='dashed';acceptFiles(e.dataTransfer.files)};showFiles();
  }else if(step===2){stage.innerHTML=`<h2>Врач и доступ</h2><label class="field">Назначить врача<select name="doctor">${staff.filter(s=>s.role==='Врач'&&s.status==='Активен').map(s=>`<option>${escapeHTML(s.name)}</option>`).join('')}</select></label><label class="field">Клиника<select name="clinic">${clinics.map(c=>`<option>${escapeHTML(c.name.replace('FamilyDent · ',''))}</option>`).join('')}</select></label><label class="row small"><input type="checkbox" name="notify" ${fields.notify?'checked':''}> Уведомить врача о новом исследовании</label><div class="info-box"><strong>Персональный доступ</strong><p>Пациент не получит доступ автоматически. Создайте временную ссылку в карточке исследования.</p></div>`;$('[name=doctor]').value=fields.doctor;$('[name=clinic]').value=fields.clinic;
  }else{stage.innerHTML=`<h2>Проверьте перед сохранением</h2><dl class="key-value"><dt>Пациент</dt><dd>${escapeHTML(fields.name)}</dd><dt>Дата рождения</dt><dd>${escapeHTML(fields.dob.split('-').reverse().join('.'))}</dd><dt>Исследование</dt><dd>${escapeHTML(fields.title)}</dd><dt>Врач</dt><dd>${escapeHTML(fields.doctor)}</dd><dt>Клиника</dt><dd>${escapeHTML(fields.clinic)}</dd><dt>Файлов выбрано</dt><dd>${files.length}</dd></dl><div class="notice">Проверены расширение и размер выбранных файлов.</div><div class="info-box"><strong>Сохранится карточка исследования</strong><p>Файлы останутся на вашем компьютере. Передача DICOM в архив и отправка email станут доступны после подключения сервера.</p></div>`}
 }
 function capture(){if(step===1){for(const key of ['name','dob','title','type'])fields[key]=$('[name='+key+']').value.trim()}if(step===2){fields.doctor=$('[name=doctor]').value;fields.clinic=$('[name=clinic]').value;fields.notify=$('[name=notify]').checked}}
 $('#upload-back').onclick=()=>{capture();step--;paintStep()};
 $('#upload-form').onsubmit=e=>{e.preventDefault();capture();if(step===1&&!files.length){$('#upload-error').hidden=false;$('#upload-error').textContent='Добавьте хотя бы один файл DICOM или ZIP-архив.';return}if(step===2&&!fields.doctor){toast('Сначала добавьте активного врача в разделе управления командой');return}if(step<3){step++;paintStep();return}const id='FD-L'+Date.now().toString().slice(-7);studies.unshift({id,name:fields.name,dob:fields.dob.split('-').reverse().join('.'),title:fields.title,type:fields.type,date:new Date().toLocaleDateString('ru-RU'),time:new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}),fresh:true,local:true,doctor:fields.doctor});storage.set('studies',studies);log('Создана локальная карточка исследования',id+' · '+fields.name);stage.innerHTML=`<div class="notice">Карточка исследования сохранена</div><h2>${escapeHTML(fields.name)}</h2><p>${escapeHTML(fields.title)} · ${escapeHTML(id)}</p><p class="muted small">Файлы не передавались на сервер. Уведомление врачу не отправлено.</p><a class="btn dark" href="doctor.html">Перейти к исследованиям →</a>`;$('.form-actions').hidden=true;$$('[data-step-label]').forEach(e=>e.classList.remove('active'))};paintStep();
}
/* Administration: editable staff, clinics, local link revocation and audit. */
if(page==='admin'){
 let tab=params.get('tab')==='audit'?'audit':'doctors';
 function renderAdmin(){
  $$('[data-admin-tab]').forEach(b=>b.setAttribute('aria-selected',b.dataset.adminTab===tab));const query=$('#admin-search').value.toLocaleLowerCase('ru');const container=$('#admin-content');$('#invite').textContent=tab==='clinics'?'Добавить клинику':'Пригласить сотрудника';$('#invite').hidden=tab==='audit'||tab==='access';
  if(tab==='doctors'){
   const rows=staff.filter(s=>(s.name+' '+s.email).toLocaleLowerCase('ru').includes(query));$('#admin-count').textContent=`Сотрудников: ${rows.length}`;
   container.innerHTML=`<div class="table-wrap"><table class="admin-table"><thead><tr><th>Сотрудник</th><th>Роль</th><th>Клиника</th><th>Доступ</th><th>Действие</th></tr></thead><tbody>${rows.map(s=>`<tr data-od-id="staff-${s.id}"><td><strong style="font-weight:500">${escapeHTML(s.name)}</strong><p class="muted small">${escapeHTML(s.email)}</p></td><td><select data-role="${s.id}" aria-label="Роль ${escapeHTML(s.name)}">${['Врач','Сотрудник','Администратор'].map(r=>`<option ${s.role===r?'selected':''}>${r}</option>`).join('')}</select></td><td>${escapeHTML(s.clinic)}</td><td><span class="badge ${s.status==='Активен'?'good':s.status==='Приглашён'?'pending':'neutral'}">${s.status}</span></td><td><button class="btn ghost" data-block="${s.id}">${s.status==='Приостановлен'?'Восстановить':'Ограничить'}</button></td></tr>`).join('')}</tbody></table>${rows.length?'':'<p class="empty">Сотрудники не найдены</p>'}</div>`;
   $$('[data-role]').forEach(select=>select.onchange=()=>{const s=staff.find(s=>s.id===select.dataset.role);s.role=select.value;storage.set('staff',staff);log('Изменена роль сотрудника',s.name+' · '+s.role);toast('Роль изменена локально')});
   $$('[data-block]').forEach(b=>b.onclick=()=>{const s=staff.find(s=>s.id===b.dataset.block),restore=s.status==='Приостановлен';modal(restore?'Восстановить доступ?':'Ограничить доступ?',`<p>${escapeHTML(s.name)} · ${escapeHTML(s.email)}</p><p>${restore?'Сотрудник снова появится в списке активных.':'Сотрудник не будет доступен для назначения новых исследований.'} Изменение применяется к локальным данным прототипа.</p><button class="btn dark" id="confirm-block">${restore?'Восстановить':'Ограничить доступ'}</button>`);$('#confirm-block').onclick=()=>{s.status=restore?'Активен':'Приостановлен';storage.set('staff',staff);log(restore?'Восстановлен доступ':'Ограничен доступ',s.name);$('#dialog').close();renderAdmin()}});
  }else if(tab==='clinics'){
   const rows=clinics.filter(c=>(c.name+' '+c.address).toLocaleLowerCase('ru').includes(query));$('#admin-count').textContent=`Клиник: ${rows.length}`;
   container.innerHTML=`<div class="stack panel-pad">${rows.map(c=>`<article class="info-box"><div class="row between"><h3>${escapeHTML(c.name)}</h3><span class="badge good">${escapeHTML(c.status)}</span></div><p>${escapeHTML(c.address)}</p><p>Сотрудников: ${staff.filter(s=>c.name.includes(s.clinic)).length}</p></article>`).join('')||'<p class="empty">Клиники не найдены</p>'}</div>`;
  }else if(tab==='access'){
   const link=storage.get('link',null),revoked=storage.get('link-revoked',false);$('#admin-count').textContent='Персональные ссылки';
   container.innerHTML=link?`<div class="panel-pad"><h3>Мария Соколова · FD-260184</h3><p class="muted small" style="margin:12px 0">${escapeHTML(link.email)} · до ${new Date(link.expires).toLocaleDateString('ru-RU')}</p><span class="badge ${revoked?'neutral':'good'}">${revoked?'Отозвана':Date.now()>link.expires?'Истекла':'Действует'}</span><div class="row" style="margin-top:20px"><button class="btn" id="manage-link">Создать новую</button>${!revoked?'<button class="btn dark" id="revoke-link">Отозвать ссылку</button>':''}</div><p class="muted small" style="margin-top:20px">Состояние ссылки хранится только в текущем браузере.</p></div>`:`<div class="empty">Временные ссылки ещё не созданы.<br><button class="btn" id="manage-link" style="margin-top:18px">Создать ссылку пациенту</button></div>`;
   $('#manage-link').onclick=shareDialog;$('#revoke-link')?.addEventListener('click',()=>{storage.set('link-revoked',true);log('Отозвана ссылка пациенту','FD-260184');renderAdmin();toast('Ссылка отозвана в текущем браузере')});
  }else{
   const rows=audit.filter(e=>(e.actor+' '+e.event+' '+e.detail).toLocaleLowerCase('ru').includes(query));$('#admin-count').textContent=`Событий: ${rows.length}`;
   container.innerHTML='<div class="audit-list">'+rows.map((e,i)=>`<article class="audit-event" data-od-id="audit-${i}"><span class="mono muted">${escapeHTML(e.time)}</span><div><h3 style="font-size:12px">${escapeHTML(e.event)}</h3><p class="muted small">${escapeHTML(e.detail)}</p></div><span class="muted">${escapeHTML(e.actor)}</span></article>`).join('')+(rows.length?'':'<p class="empty">События не найдены</p>')+'</div>';
  }
 }
 $$('[data-admin-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.adminTab;$('#admin-search').value='';renderAdmin()});$('#admin-search').oninput=renderAdmin;
 $('#invite').onclick=()=>{
  if(tab==='clinics'){modal('Добавить клинику','<form id="clinic-form"><label class="field">Название<input required name="name" placeholder="Название филиала"></label><label class="field">Адрес<input required name="address" placeholder="Город, улица, дом"></label><button class="btn dark" type="submit">Добавить клинику</button></form>');$('#clinic-form').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);clinics.push({name:'FamilyDent · '+f.get('name').trim(),address:f.get('address').trim(),status:'Активна'});storage.set('clinics',clinics);log('Добавлена клиника',f.get('name'));$('#dialog').close();renderAdmin()};return}
  modal('Пригласить сотрудника',`<form id="invite-form"><label class="field">ФИО<input name="name" required placeholder="Фамилия Имя"></label><label class="field">Рабочий email<input name="email" type="email" required placeholder="doctor@example.test"></label><label class="field">Роль<select name="role"><option>Врач</option><option>Сотрудник</option><option>Администратор</option></select></label><label class="field">Клиника<select name="clinic">${clinics.map(c=>`<option>${escapeHTML(c.name.replace('FamilyDent · ',''))}</option>`).join('')}</select></label><p>Приглашение сохранится локально. Отправка email ещё не подключена.</p><button class="btn dark" type="submit">Подготовить приглашение</button></form>`);
  $('#invite-form').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target),email=String(f.get('email')).trim().toLowerCase();if(staff.some(s=>s.email===email)){toast('Сотрудник с этим email уже есть в команде');return}staff.push({id:'u'+Date.now(),name:String(f.get('name')).trim(),email,role:f.get('role'),clinic:f.get('clinic'),status:'Приглашён'});storage.set('staff',staff);log('Подготовлено приглашение',email);$('#dialog').close();renderAdmin();toast('Приглашение подготовлено. Письмо не отправлено.')};
 };renderAdmin();
}
/* Stable inspectable handles for interactive controls and meaningful content. */
let inspectableSerial=0;
function inspectable(){$$('main,section,article,header,footer,nav,aside,h1,h2,h3,button,a,input,select,textarea').forEach(el=>{if(!el.dataset.odId)el.dataset.odId=page+'-'+el.tagName.toLowerCase()+'-'+(++inspectableSerial)})}
inspectable();new MutationObserver(()=>inspectable()).observe(document.body,{childList:true,subtree:true});
