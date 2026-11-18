'use strict';
window.LRFrequency = (() => {
  let dataset, pending, ui, audioData, queue=[], queuePosition=0, gapTimer, queueMode='single', phase='idle', pausedFrom=null, remainingGap=0, gapDeadline=0, cycle=1, playVersion=0;
  const state = {query:'', min:0, sort:'frequency', audio:'all', speed:1, gap:3, loop:true};
  const isCurrent = () => location.hash.replace(/^#\/?/,'') === 'lr-frequency';
  async function load() {
    if (dataset) return dataset;
    if (!pending) pending = fetch('lr-frequency.json').then(response => {
      if (!response.ok) throw Error('L&R '+response.status);
      return response.json();
    }).then(async value => {const response=await fetch('lr-audio.json?v=20261119-local-speaking');if(!response.ok)throw Error('Audio '+response.status);audioData=await response.json();dataset=value;return value;}).catch(error => {pending=null; throw error;});
    return pending;
  }
  function filteredGroups() {
    const term=state.query.trim().toLowerCase();
    const groups = dataset.groups.filter(g => g.frequency>=state.min && (state.audio==='all'||(state.audio==='original'?originalCount(g)>0:state.audio==='complete'?originalCount(g)===7:originalCount(g)<7)) && (!term ||
      [g.id,g.title,...g.sentences].some(value=>value.toLowerCase().includes(term))));
    groups.sort(state.sort==='date' ? (a,b)=>b.firstRecordedDate.localeCompare(a.firstRecordedDate)||a.rank-b.rank : (a,b)=>a.rank-b.rank);
    return groups;
  }
  function results() {
    const {esc}=ui, groups=filteredGroups();
    const playable=groups.reduce((sum,group)=>sum+tracks(group).filter(Boolean).length,0);
    document.querySelector('#lr-continuous').disabled=!playable;
    document.querySelector('#lr-list-audio-count').textContent=`当前筛选有 ${groups.filter(group=>tracks(group).some(Boolean)).length} 组、${playable} 句可播放`;
    document.querySelector('#lr-result-count').textContent = `${groups.length} / ${dataset.meta.groupCount} 组`;
    document.querySelector('#lr-results').innerHTML = groups.length ? groups.map(g => `
      <details class="lr-row">
        <summary class="lr-columns">
          <span class="lr-rank">${String(g.rank).padStart(2,'0')}</span>
          <span class="lr-topic"><strong>${esc(g.title)}</strong><small>${esc(g.id)} · 7 句${g.hasVariants?' · 存在异文':''}</small><small class="lr-audio-coverage">${coverage(g)}</small></span>
          <span class="lr-frequency"><b>${g.frequency}<small> 次</small></b><span class="lr-bar" aria-hidden="true"><i style="width:${g.frequency/9*100}%"></i></span></span>
          <span class="lr-date"><small>首次记录</small>${esc(g.firstRecordedDate)}</span>
          <span class="lr-expand" aria-hidden="true">＋</span>
        </summary>
        <div class="lr-detail"><p>首次记录：原数组第 ${g.firstRecordIndex} 条${g.hasVariants?'。同组后续记录存在句子异文；以下采用首次记录的完整 7 句。':'。以下采用首次记录原文。'}</p>
          <div class="lr-group-audio"><button class="btn small" data-lr-group="${g.id}" ${tracks(g).some(Boolean)?'':'disabled'}>${ui.icon('sound')} 播放本组已有音频</button><span>${tracks(g).filter(Boolean).length} / 7 句可播放</span></div>
          <ol>${g.sentences.map((sentence,index)=>{const track=tracks(g)[index];return `<li id="lr-sentence-${g.id}-${index}"><span>${esc(sentence)}</span><div class="lr-sentence-audio">${track?`<button class="btn small" data-lr-play="${g.id}" data-lr-index="${index}" aria-label="播放 ${g.id} 第 ${index+1} 句">${ui.icon('sound')} 播放第 ${index+1} 句</button><small >${sourceLabel(track)}</small>`:'<small>暂未找到文字一致的原站音频</small>'}</div></li>`;}).join('')}</ol>
        </div>
      </details>`).join('') : '<div class="empty"><h3>没有找到符合条件的组别。</h3><p>试试其他主题、英文原句或组号，或清除筛选。</p></div>';
  }
  function content() {
    stop();
    const {esc,icon} = ui, {meta} = dataset;
    document.querySelector('#lr-content').innerHTML = `
      <div class="lr-stats stats-row">
        <div class="stat"><strong>${meta.groupCount}</strong><span>独立组别</span></div>
        <div class="stat"><strong>${meta.sentenceCount}</strong><span>原文句子</span></div>
        <div class="stat"><strong>${meta.groupedRecords}</strong><span>累计有效记录</span></div>
        <div class="stat"><strong>${meta.variantGroups}</strong><span>存在异文的组别</span></div>
      </div>
      <section class="lr-overview" aria-label="频次分布与统计口径">
        <div class="lr-distribution"><h2>频次分布 <small>各频次对应的组数</small></h2>
          <div class="lr-chart">${Object.entries(meta.distribution).map(([frequency,count])=>`<div class="lr-chart-column"><span>${count} 组</span><div class="lr-chart-track"><i style="height:${count/32*100}%"></i></div><small>${frequency} 次</small></div>`).join('')}</div>
        </div>
        <div class="lr-method"><h2>沿用之前的统计口径</h2><p>按原始样本中每个 group_id 的实际出现次数统计；同频按首次出现的数组位置排序。</p><p><b>日期为首次记录日期。</b>现有统计没有最近一次出现日期，累计频次也不代表考试概率。</p><details><summary>查看样本与原文说明</summary><p>原始样本 259 条，其中 258 条归入 90 组；另 1 条为未归组的空白记录，未计入频次。不使用 catalog_frequency。</p><p>每组原文取首次记录，保留原始拼写、语法和标点；50 组存在后续句子异文。这里沿用此前 PDF 的统计快照。</p></details>
          <a class="lr-source" href="lr-frequency-source.pdf" download="L&R_90组_实际频次排序.pdf">${icon('book')} 下载原始统计 PDF ${icon('arrow')}</a>
        </div>
      </section>
      <aside class="lr-audio-note"><b>${icon('sound')} 音频已按原句核对</b><p>${audioData.meta.originalGroups} 组共 ${audioData.meta.originalSentences} 句配有原站音频，其中 ${audioData.meta.completeOriginalGroups} 组的 7 句均匹配。其余 ${audioData.meta.missingSentences} 句暂未找到文字一致的录音，保留缺少音频提示。音频已缓存到本机；“原站音频”指 Wofo 录音来源。</p></aside>
      <section class="lr-ranking" aria-label="L&R 组别频次排行">
        <div class="lr-ranking-heading"><h2 class="section-title">从熟悉的主题开始。</h2><span id="lr-result-count" role="status" aria-live="polite"></span></div>
        <div class="lr-tools">
          <label class="lr-search">搜索主题、组号或原句<input id="lr-search" type="search" placeholder="例如 Museum、G041、coffee" value="${esc(state.query)}"></label>
          <label>出现次数<select id="lr-min"><option value="0">全部频次</option><option value="5">5 次及以上</option><option value="3">3 次及以上</option><option value="2">2 次及以上</option></select></label>
          <label>排序<select id="lr-sort"><option value="frequency">累计频次优先</option><option value="date">首次记录日期倒序</option></select></label>
          <label>音频<select id="lr-audio-filter"><option value="all">全部组别</option><option value="original">有原站音频</option><option value="complete">全组原站音频</option><option value="missing">暂缺部分原站音频</option></select></label>
          <button class="btn small" id="lr-clear">清除筛选</button>
        </div>
        <div class="lr-continuous-bar"><button class="btn primary" id="lr-continuous">${icon('sound')} 连续播放当前列表</button><label class="lr-loop-option"><input type="checkbox" id="lr-loop" ${state.loop?'checked':''}> 播完循环</label><span id="lr-list-audio-count" role="status"></span><p>按开始时的筛选和排序逐组播放，自动跳过缺失音频。取消循环后，播完列表即停止。</p></div>
        <div class="lr-table-head lr-columns" aria-hidden="true"><span>排名</span><span>主题 / 点击展开 7 句原文</span><span>累计出现</span><span>首次记录日期</span><span></span></div>
        <div id="lr-results"></div>
      </section>
      <aside class="lr-player" id="lr-player-panel" hidden aria-label="L&R 音频播放器"><div class="lr-player-title"><strong id="lr-track-title"></strong><span class="lr-player-buttons"><button class="btn small" id="lr-toggle">暂停</button><button class="btn small" id="lr-stop" aria-label="停止并关闭播放器">停止 ${icon('close')}</button></span></div><p id="lr-track-sentence"></p><div class="lr-player-controls"><audio id="lr-player" controls preload="none" aria-label="当前复述句子音频"></audio><label>语速<select id="lr-speed"><option value="0.8">0.8×</option><option value="1">1×</option><option value="1.2">1.2×</option></select></label><label>句间停顿<select id="lr-gap"><option value="0">0 秒</option><option value="3">3 秒</option><option value="5">5 秒</option><option value="8">8 秒</option></select></label></div><small id="lr-queue-status" role="status" aria-live="polite"></small><small id="lr-track-source" role="status" aria-live="polite"></small></aside>`;
    document.querySelector('#lr-min').value=String(state.min);
    document.querySelector('#lr-sort').value=state.sort;
    document.querySelector('#lr-audio-filter').value=state.audio;
    document.querySelector('#lr-search').addEventListener('input', event=>{state.query=event.target.value;results();});
    document.querySelector('#lr-min').addEventListener('change', event=>{state.min=Number(event.target.value);results();});
    document.querySelector('#lr-sort').addEventListener('change', event=>{state.sort=event.target.value;results();});
    document.querySelector('#lr-audio-filter').addEventListener('change', event=>{state.audio=event.target.value;results();});
    document.querySelector('#lr-clear').addEventListener('click', ()=>{state.query='';state.min=0;state.sort='frequency';state.audio='all';content();document.querySelector('#lr-search').focus();});
    document.querySelector('#lr-speed').value=String(state.speed);
    document.querySelector('#lr-gap').value=String(state.gap);
    document.querySelector('#lr-speed').onchange=event=>{state.speed=Number(event.target.value);document.querySelector('#lr-player').playbackRate=state.speed;};
    document.querySelector('#lr-gap').onchange=event=>{state.gap=Number(event.target.value);if(phase==='waiting')scheduleNext(state.gap*1000);else if(phase==='paused'&&pausedFrom==='waiting')remainingGap=state.gap*1000;};
    document.querySelector('#lr-loop').onchange=event=>{state.loop=event.target.checked;updatePlayer();};
    document.querySelector('#lr-continuous').onclick=()=>startQueue(filteredGroups(),'continuous');
    document.querySelector('#lr-stop').onclick=stop;
    document.querySelector('#lr-toggle').onclick=togglePause;
    const player=document.querySelector('#lr-player');
    player.onended=()=>{if(!queue.length||phase==='idle')return;if(hasNext())scheduleNext(state.gap*1000);else{phase='complete';updatePlayer();}};
    player.onplay=()=>{if(!queue.length)return;if(phase==='paused'&&pausedFrom==='waiting'){player.pause();return;}phase='playing';pausedFrom=null;updatePlayer();};
    player.onpause=()=>{if(phase==='playing'&&!player.ended){phase='paused';pausedFrom='playing';updatePlayer();}};
    player.onerror=()=>{if(phase==='idle')return;clearTimeout(gapTimer);playVersion++;phase='error';updatePlayer();};
    results();
  }
  function tracks(group) {return audioData.groups[group.id]||[];}
  function originalCount(group) {return tracks(group).filter(a=>a?.kind==='original').length;}
  function coverage(group) {const original=originalCount(group);return original?`原站音频 ${original}/7`:'暂无原站音频';}
  function sourceLabel(track) {return `原站音频 · ${track.testId.replace('mock-','Mock ')}`;}
  function hasNext(){return queuePosition+1<queue.length||(queueMode==='continuous'&&state.loop&&queue.length>0);}
  function updatePlayer(){
    const label=document.querySelector('#lr-queue-status'),button=document.querySelector('#lr-toggle'),source=document.querySelector('#lr-track-source');
    if(!label||!button||!source||!queue.length)return;
    const name=queueMode==='continuous'?'连续播放':queueMode==='group'?'本组播放':'单句播放';
    const status={loading:'正在加载',playing:'播放中',waiting:'句间停顿',paused:'已暂停',complete:'播放完成',error:'音频加载失败'}[phase]||'';
    label.textContent=`${name} · ${queuePosition+1} / ${queue.length} 句${queueMode==='continuous'?` · 第 ${cycle} 轮${state.loop?' · 循环开启':''}`:''} · ${status}`;
    button.textContent=phase==='paused'?'继续播放':phase==='error'?'重试播放':phase==='complete'?'重新播放':'暂停';
    button.disabled=phase==='loading';
    source.textContent=phase==='error'?'音频暂时无法加载，请点击重试播放。':sourceLabel(queue[queuePosition].track);
  }
  function scheduleNext(delay){
    clearTimeout(gapTimer);phase='waiting';remainingGap=delay;gapDeadline=Date.now()+delay;updatePlayer();
    gapTimer=setTimeout(()=>{if(phase!=='waiting'||!queue.length||!isCurrent())return;if(queuePosition+1<queue.length)queuePosition++;else if(queueMode==='continuous'&&state.loop){queuePosition=0;cycle++;}else{phase='complete';updatePlayer();return;}playCurrent();},delay);
  }
  function stop(){
    clearTimeout(gapTimer);playVersion++;phase='idle';pausedFrom=null;remainingGap=0;queue=[];queuePosition=0;cycle=1;
    const audio=document.querySelector('#lr-player');if(audio){audio.pause();audio.removeAttribute('src');audio.load();document.querySelector('#lr-player-panel').hidden=true;}
    document.querySelectorAll('.lr-sentence-playing').forEach(el=>el.classList.remove('lr-sentence-playing'));
  }
  function startQueue(groups,mode,selected=null){
    stop();queueMode=mode;
    queue=groups.flatMap(group=>tracks(group).map((track,index)=>({track,index,group})).filter(item=>item.track&&(selected===null||selected===item.index)));
    if(queue.length)playCurrent();
  }
  function attemptPlay(audio,version){
    audio.play().catch(()=>{if(version!==playVersion||!isCurrent()||phase==='idle')return;phase='paused';pausedFrom='playing';updatePlayer();document.querySelector('#lr-track-source').textContent='浏览器暂停了自动播放，请点击继续播放。';});
  }
  function togglePause(){
    const audio=document.querySelector('#lr-player');if(!audio||!queue.length)return;
    if(phase==='paused'){
      if(pausedFrom==='waiting'){pausedFrom=null;scheduleNext(remainingGap);}else{phase='loading';updatePlayer();attemptPlay(audio,++playVersion);}
    }else if(phase==='complete'){queuePosition=0;cycle=1;playCurrent();}
    else if(phase==='error'){playCurrent();}
    else if(phase==='waiting'){remainingGap=Math.max(0,gapDeadline-Date.now());clearTimeout(gapTimer);phase='paused';pausedFrom='waiting';updatePlayer();}
    else if(phase==='playing'){phase='paused';pausedFrom='playing';audio.pause();updatePlayer();}
  }
  function playCurrent(){
    const item=queue[queuePosition];if(!item||!isCurrent())return;
    clearTimeout(gapTimer);phase='loading';pausedFrom=null;const version=++playVersion;
    const {group,index,track}=item,audio=document.querySelector('#lr-player');
    document.querySelector('#lr-player-panel').hidden=false;
    document.querySelector('#lr-track-title').textContent=`${group.title} · 第 ${index+1} / 7 句`;
    document.querySelector('#lr-track-sentence').textContent=group.sentences[index];
    document.querySelectorAll('.lr-sentence-playing').forEach(el=>el.classList.remove('lr-sentence-playing'));
    document.querySelector(`#lr-sentence-${group.id}-${index}`)?.classList.add('lr-sentence-playing');
    updatePlayer();audio.src=track.src;audio.playbackRate=state.speed;attemptPlay(audio,version);
  }
  document.addEventListener('click',event=>{const button=event.target.closest('[data-lr-play],[data-lr-group]');if(!button||!dataset||button.disabled)return;const group=dataset.groups.find(g=>g.id===(button.dataset.lrPlay||button.dataset.lrGroup));if(!group)return;const single=Boolean(button.dataset.lrPlay);startQueue([group],single?'single':'group',single?Number(button.dataset.lrIndex):null);});
  window.addEventListener('hashchange',()=>{if(!isCurrent())stop();});
  async function render(context) {
    ui=context;
    document.querySelector('#app').innerHTML = ui.header('lr')+`<main class="wrap lr-page"><section class="lr-hero"><div><div class="eyebrow">LISTEN & REPEAT / FREQUENCY NOTES</div><h1>L & R，<em>有据可循地复习。</em></h1><p>把之前整理的出现频次，放回你的学习书桌。<br>按主题查找，展开原句，再决定今天练哪一组。</p></div><a class="btn" href="#/catalog/speaking">口语新题 ${ui.icon('arrow')}</a></section><div id="lr-content"><p class="lr-loading" role="status">正在加载之前的频次统计…</p></div>${ui.footer()}</main>`;
    try {await load();if(isCurrent())content();}
    catch(error) {if(isCurrent()){document.querySelector('#lr-content').innerHTML='<div class="empty"><h3>频次统计暂时未加载成功。</h3><button class="btn" id="lr-retry">重新加载</button></div>';document.querySelector('#lr-retry').onclick=()=>render(ui);}console.error(error);}
  }
  return {render};
})();
