var B=globalThis,W=B.ShadowRoot&&(B.ShadyCSS===void 0||B.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Y=Symbol(),ve=new WeakMap,I=class{constructor(e,t,s){if(this._$cssResult$=!0,s!==Y)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(W&&e===void 0){let s=t!==void 0&&t.length===1;s&&(e=ve.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),s&&ve.set(t,e))}return e}toString(){return this.cssText}},ye=a=>new I(typeof a=="string"?a:a+"",void 0,Y),k=(a,...e)=>{let t=a.length===1?a[0]:e.reduce((s,i,n)=>s+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+a[n+1],a[0]);return new I(t,a,Y)},be=(a,e)=>{if(W)a.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let s=document.createElement("style"),i=B.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=t.cssText,a.appendChild(s)}},Q=W?a=>a:a=>a instanceof CSSStyleSheet?(e=>{let t="";for(let s of e.cssRules)t+=s.cssText;return ye(t)})(a):a;var{is:We,defineProperty:Ke,getOwnPropertyDescriptor:Fe,getOwnPropertyNames:je,getOwnPropertySymbols:qe,getPrototypeOf:Ge}=Object,K=globalThis,we=K.trustedTypes,Ve=we?we.emptyScript:"",Ze=K.reactiveElementPolyfillSupport,N=(a,e)=>a,X={toAttribute(a,e){switch(e){case Boolean:a=a?Ve:null;break;case Object:case Array:a=a==null?a:JSON.stringify(a)}return a},fromAttribute(a,e){let t=a;switch(e){case Boolean:t=a!==null;break;case Number:t=a===null?null:Number(a);break;case Object:case Array:try{t=JSON.parse(a)}catch{t=null}}return t}},xe=(a,e)=>!We(a,e),$e={attribute:!0,type:String,converter:X,reflect:!1,useDefault:!1,hasChanged:xe};Symbol.metadata??=Symbol("metadata"),K.litPropertyMetadata??=new WeakMap;var b=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=$e){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(e,s,t);i!==void 0&&Ke(this.prototype,e,i)}}static getPropertyDescriptor(e,t,s){let{get:i,set:n}=Fe(this.prototype,e)??{get(){return this[t]},set(r){this[t]=r}};return{get:i,set(r){let d=i?.call(this);n?.call(this,r),this.requestUpdate(e,d,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??$e}static _$Ei(){if(this.hasOwnProperty(N("elementProperties")))return;let e=Ge(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(N("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(N("properties"))){let t=this.properties,s=[...je(t),...qe(t)];for(let i of s)this.createProperty(i,t[i])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[s,i]of t)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[t,s]of this.elementProperties){let i=this._$Eu(t,s);i!==void 0&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let s=new Set(e.flat(1/0).reverse());for(let i of s)t.unshift(Q(i))}else e!==void 0&&t.push(Q(e));return t}static _$Eu(e,t){let s=t.attribute;return s===!1?void 0:typeof s=="string"?s:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return be(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){let s=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,s);if(i!==void 0&&s.reflect===!0){let n=(s.converter?.toAttribute!==void 0?s.converter:X).toAttribute(t,s.type);this._$Em=e,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(e,t){let s=this.constructor,i=s._$Eh.get(e);if(i!==void 0&&this._$Em!==i){let n=s.getPropertyOptions(i),r=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:X;this._$Em=i;let d=r.fromAttribute(t,n.type);this[i]=d??this._$Ej?.get(i)??d,this._$Em=null}}requestUpdate(e,t,s,i=!1,n){if(e!==void 0){let r=this.constructor;if(i===!1&&(n=this[e]),s??=r.getPropertyOptions(e),!((s.hasChanged??xe)(n,t)||s.useDefault&&s.reflect&&n===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,s))))return;this.C(e,t,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:i,wrapped:n},r){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),n!==!0||r!==void 0)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),i===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,n]of s){let{wrapped:r}=n,d=this[i];r!==!0||this._$AL.has(i)||d===void 0||this.C(i,void 0,n,d)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(t)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};b.elementStyles=[],b.shadowRootOptions={mode:"open"},b[N("elementProperties")]=new Map,b[N("finalized")]=new Map,Ze?.({ReactiveElement:b}),(K.reactiveElementVersions??=[]).push("2.1.2");var re=globalThis,ke=a=>a,F=re.trustedTypes,Ae=F?F.createPolicy("lit-html",{createHTML:a=>a}):void 0,Ce="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,De="?"+$,Je=`<${De}>`,S=document,L=()=>S.createComment(""),O=a=>a===null||typeof a!="object"&&typeof a!="function",oe=Array.isArray,Ye=a=>oe(a)||typeof a?.[Symbol.iterator]=="function",ee=`[ 	
\f\r]`,R=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ze=/-->/g,Se=/>/g,A=RegExp(`>|${ee}(?:([^\\s"'>=/]+)(${ee}*=${ee}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Pe=/'/g,Ee=/"/g,Ie=/^(?:script|style|textarea|title)$/i,le=a=>(e,...t)=>({_$litType$:a,strings:e,values:t}),o=le(1),dt=le(2),ht=le(3),P=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Te=new WeakMap,z=S.createTreeWalker(S,129);function Ne(a,e){if(!oe(a)||!a.hasOwnProperty("raw"))throw Error("invalid template strings array");return Ae!==void 0?Ae.createHTML(e):e}var Qe=(a,e)=>{let t=a.length-1,s=[],i,n=e===2?"<svg>":e===3?"<math>":"",r=R;for(let d=0;d<t;d++){let c=a[d],p,_,h=-1,y=0;for(;y<c.length&&(r.lastIndex=y,_=r.exec(c),_!==null);)y=r.lastIndex,r===R?_[1]==="!--"?r=ze:_[1]!==void 0?r=Se:_[2]!==void 0?(Ie.test(_[2])&&(i=RegExp("</"+_[2],"g")),r=A):_[3]!==void 0&&(r=A):r===A?_[0]===">"?(r=i??R,h=-1):_[1]===void 0?h=-2:(h=r.lastIndex-_[2].length,p=_[1],r=_[3]===void 0?A:_[3]==='"'?Ee:Pe):r===Ee||r===Pe?r=A:r===ze||r===Se?r=R:(r=A,i=void 0);let w=r===A&&a[d+1].startsWith("/>")?" ":"";n+=r===R?c+Je:h>=0?(s.push(p),c.slice(0,h)+Ce+c.slice(h)+$+w):c+$+(h===-2?d:w)}return[Ne(a,n+(a[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),s]},H=class a{constructor({strings:e,_$litType$:t},s){let i;this.parts=[];let n=0,r=0,d=e.length-1,c=this.parts,[p,_]=Qe(e,t);if(this.el=a.createElement(p,s),z.currentNode=this.el.content,t===2||t===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(i=z.nextNode())!==null&&c.length<d;){if(i.nodeType===1){if(i.hasAttributes())for(let h of i.getAttributeNames())if(h.endsWith(Ce)){let y=_[r++],w=i.getAttribute(h).split($),U=/([.?@])?(.*)/.exec(y);c.push({type:1,index:n,name:U[2],strings:w,ctor:U[1]==="."?se:U[1]==="?"?ie:U[1]==="@"?ae:T}),i.removeAttribute(h)}else h.startsWith($)&&(c.push({type:6,index:n}),i.removeAttribute(h));if(Ie.test(i.tagName)){let h=i.textContent.split($),y=h.length-1;if(y>0){i.textContent=F?F.emptyScript:"";for(let w=0;w<y;w++)i.append(h[w],L()),z.nextNode(),c.push({type:2,index:++n});i.append(h[y],L())}}}else if(i.nodeType===8)if(i.data===De)c.push({type:2,index:n});else{let h=-1;for(;(h=i.data.indexOf($,h+1))!==-1;)c.push({type:7,index:n}),h+=$.length-1}n++}}static createElement(e,t){let s=S.createElement("template");return s.innerHTML=e,s}};function E(a,e,t=a,s){if(e===P)return e;let i=s!==void 0?t._$Co?.[s]:t._$Cl,n=O(e)?void 0:e._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(a),i._$AT(a,t,s)),s!==void 0?(t._$Co??=[])[s]=i:t._$Cl=i),i!==void 0&&(e=E(a,i._$AS(a,e.values),i,s)),e}var te=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:s}=this._$AD,i=(e?.creationScope??S).importNode(t,!0);z.currentNode=i;let n=z.nextNode(),r=0,d=0,c=s[0];for(;c!==void 0;){if(r===c.index){let p;c.type===2?p=new M(n,n.nextSibling,this,e):c.type===1?p=new c.ctor(n,c.name,c.strings,this,e):c.type===6&&(p=new ne(n,this,e)),this._$AV.push(p),c=s[++d]}r!==c?.index&&(n=z.nextNode(),r++)}return z.currentNode=S,i}p(e){let t=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}},M=class a{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,i){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=E(this,e,t),O(e)?e===l||e==null||e===""?(this._$AH!==l&&this._$AR(),this._$AH=l):e!==this._$AH&&e!==P&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Ye(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==l&&O(this._$AH)?this._$AA.nextSibling.data=e:this.T(S.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:s}=e,i=typeof s=="number"?this._$AC(e):(s.el===void 0&&(s.el=H.createElement(Ne(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(t);else{let n=new te(i,this),r=n.u(this.options);n.p(t),this.T(r),this._$AH=n}}_$AC(e){let t=Te.get(e.strings);return t===void 0&&Te.set(e.strings,t=new H(e)),t}k(e){oe(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,s,i=0;for(let n of e)i===t.length?t.push(s=new a(this.O(L()),this.O(L()),this,this.options)):s=t[i],s._$AI(n),i++;i<t.length&&(this._$AR(s&&s._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let s=ke(e).nextSibling;ke(e).remove(),e=s}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,i,n){this.type=1,this._$AH=l,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=n,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=l}_$AI(e,t=this,s,i){let n=this.strings,r=!1;if(n===void 0)e=E(this,e,t,0),r=!O(e)||e!==this._$AH&&e!==P,r&&(this._$AH=e);else{let d=e,c,p;for(e=n[0],c=0;c<n.length-1;c++)p=E(this,d[s+c],t,c),p===P&&(p=this._$AH[c]),r||=!O(p)||p!==this._$AH[c],p===l?e=l:e!==l&&(e+=(p??"")+n[c+1]),this._$AH[c]=p}r&&!i&&this.j(e)}j(e){e===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},se=class extends T{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===l?void 0:e}},ie=class extends T{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==l)}},ae=class extends T{constructor(e,t,s,i,n){super(e,t,s,i,n),this.type=5}_$AI(e,t=this){if((e=E(this,e,t,0)??l)===P)return;let s=this._$AH,i=e===l&&s!==l||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,n=e!==l&&(s===l||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},ne=class{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){E(this,e)}};var Xe=re.litHtmlPolyfillSupport;Xe?.(H,M),(re.litHtmlVersions??=[]).push("3.3.3");var Re=(a,e,t)=>{let s=t?.renderBefore??e,i=s._$litPart$;if(i===void 0){let n=t?.renderBefore??null;s._$litPart$=i=new M(e.insertBefore(L(),n),n,void 0,t??{})}return i._$AI(a),i};var ce=globalThis,m=class extends b{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Re(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return P}};m._$litElement$=!0,m.finalized=!0,ce.litElementHydrateSupport?.({LitElement:m});var et=ce.litElementPolyfillSupport;et?.({LitElement:m});(ce.litElementVersions??=[]).push("4.2.2");var Le=async(a,e)=>(await a.callWS({type:"sip_assistant/config",...e?{entry_id:e}:{}})).config,j=(a,e,t,s)=>a.callWS({type:"sip_assistant/save_section",entry_id:e,section:t,values:s}),q=(a,e,t,s)=>a.callWS({type:"sip_assistant/save_item",entry_id:e,kind:t,item:s}),G=(a,e,t,s)=>a.callWS({type:"sip_assistant/delete_item",entry_id:e,kind:t,item_id:s}),u=(a,e)=>{a.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:e},bubbles:!0,composed:!0}))},Oe=(a,e=!1)=>{e?history.replaceState(null,"",a):history.pushState(null,"",a),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:e}}))},He=async a=>{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(a);return}let e=document.createElement("textarea");e.value=a,e.style.position="fixed",e.style.opacity="0",document.body.appendChild(e),e.select(),document.execCommand("copy"),e.remove()};var Me={tabs:{overview:"Overview",commands:"Keypad commands",assistants:"Assistants",call:"Call flow",connection:"Connection"},common:{save:"Save",saved:"Saved",cancel:"Discard changes",delete:"Delete",delete_confirm:"Really delete?",back:"Back",loading:"Loading\u2026",error_loading:"The configuration could not be loaded.",no_entry:"SIP Assistant is not set up yet. Add the integration under Settings \u2192 Devices & services.",not_loaded:"This entry is not running. Check the logs; the SIP port may be in use.",unsaved:"Unsaved changes",form_errors:"Please check the highlighted fields.",save_failed:"Saving failed: {error}"},errors:{required:"Required",invalid_code:"1\u20138 characters from 0\u20139 and A\u2013D",code_in_use:"This code is already used",name_in_use:"This name is already used",invalid_entity:"This entity type is not supported",invalid_actions:"The actions are not valid",invalid_template:"The template is not valid",invalid_pin:"4\u201312 digits",invalid_networks:"Not a valid address or CIDR network",invalid_rtp_range:"The range must contain at least two ports",invalid_number:"Value out of range",invalid_option:"Invalid selection",port_in_use:"Port is already in use",invalid_user:"Only letters, digits and . _ ~ + -",invalid_auth:"OpenAI rejected the API key",cannot_connect:"Could not reach OpenAI to check the key"},state:{idle:"Ready",pin:"PIN entry",menu:"Keypad menu",assistant:"Voice assistant",unavailable:"Not running"},overview:{status:"Status",active_calls:"Active calls",sip_address:"SIP address",copy:"Copy",copied:"SIP address copied",how_to:"Dial this address from a softphone, SIP desk phone or analog telephone adapter.",last_caller:"Last caller",last_call:"Last call",never:"No calls yet",hang_up:"End all calls",keypad:"Keypad",keypad_hint:"This is what callers can reach with the keypad.",starts_with:"Calls start with",start_menu:"the keypad menu",key_repeat:"Repeat the menu / return to the menu",key_submit:"Finish a multi-digit code",announced:"Announced",not_announced:"Not announced",unreachable:"Unreachable (no API key)",checks:"Checks",all_good:"Everything is set up. No issues found.",check_no_api_key:"Assistants are set up, but no OpenAI API key is stored, so callers cannot reach them.",check_risky:"\u201C{name}\u201D combines web search with access to your home.",check_no_tts:"No text-to-speech engine is available. Announcements are replaced by tones.",check_open:"There is no SIP password and calls are allowed from every network.",check_nothing:"There are no keypad commands or assistants yet, so callers only hear the greeting.",go_connection:"Open connection",go_assistants:"Open assistants",go_commands:"Add a command"},commands:{add:"New command",empty:"No keypad commands yet. Create the first one, for example \u201C1\u201D for the garage door.",select:"Select a command or create a new one.",new:"New keypad command",type:"What should happen?",type_entity:"Run an entity",type_entity_desc:"Start a script or scene, trigger an automation, press a button or toggle a light or switch.",type_actions:"Custom actions",type_actions_desc:"Build any sequence of actions with the action editor.",type_announcement:"Speak a text",type_announcement_desc:"Read out a text, e.g. a sensor value through a template.",badge_menu:"Menu",badge_ai:"AI",fields:{name:"Name",code:"Keypad code",entity_id:"Entity",actions:"Actions",response:"Spoken confirmation",response_announcement:"Text",announce:"Mention in the menu announcement",ai_enabled:"Assistants may run this command",description:"Description for the assistants"},helpers:{code:"1\u20138 characters from 0\u20139 and A\u2013D. * and # are reserved.",entity_id:"Scripts and scenes are started, automations triggered, buttons pressed and other entities toggled.",actions:"The variables caller, caller_name and code are available.",response:"Optional. Templates are supported. Empty: \u201CNAME has been executed\u201D.",response_announcement:"Templates are supported, for example to read out a sensor state.",description:"Helps the assistants decide when to use this command."}},assistants:{add:"New assistant",empty:"No assistants yet. An assistant answers on its own key, e.g. \u201C0\u201D with access to your home and \u201C1\u201D with web search.",select:"Select an assistant or create a new one.",new:"New assistant",general:"General",model:"Model and voice",access:"Access and tools",behaviour:"Conversation",advanced:"Advanced model settings",starts_calls:"Starts calls",badge_home:"Devices",badge_commands:"Commands",badge_web:"Web search",badge_talk:"Conversation only",engine_live:"GPT-Live",engine_live_desc:"Full-duplex voice model that hands tools to a fast backend model. Most natural conversations.",engine_realtime:"Realtime API",engine_realtime_desc:"A single speech-to-speech model that uses the tools itself.",home_control:"Control devices",home_control_desc:"The assistant may use Home Assistant to switch and query entities.",llm_apis:"Home Assistant APIs",llm_apis_desc:"\u201CAssist\u201D controls the entities exposed to Assist.",phone_commands:"Run keypad commands",phone_commands_desc:"Keypad commands that allow it can also be run by voice.",web_search:"Web search",web_search_desc:"Look up current information such as news, weather or opening hours.",fast_interrupt:"Fast interruption",fast_interrupt_desc:"Stops the assistant as soon as you talk over it, instead of waiting for OpenAI to notice. Turn off if background noise cuts it off.",risky_title:"Web search and access to your home are both enabled",risky_text:"Web pages can contain hidden instructions (prompt injection) that trick the assistant into actions in your home. Only combine both if you accept this risk.",no_api_key:"Without an OpenAI API key this assistant cannot be reached.",effort:{none:"None",minimal:"Minimal",low:"Low",medium:"Medium",high:"High"},fields:{name:"Name",code:"Keypad code",announce:"Mention in the menu announcement",voice:"Voice",prompt:"Instructions",live_model:"GPT-Live model",backend_model:"Backend model (GPT-Live tools, web search)",reasoning_effort:"Backend reasoning effort",realtime_model:"Realtime model"},helpers:{code:"1\u20138 characters from 0\u20139 and A\u2013D. * and # are reserved.",voice:"GPT-Live offers more voices that can be typed in by name.",prompt:"Personality and behaviour. Empty: default instructions. Templates are supported.",reasoning_effort:"Lower values answer faster."}},call:{title:"Call flow",description:"What callers hear and how the keypad menu behaves.",start_menu:"Keypad menu",fields:{start:"When a call is answered, start with",greeting:"Greeting",announce_menu:"Announce the menu",menu_prompt:"Custom menu announcement",pin:"PIN",tts_engine:"Text-to-speech engine",language:"Language",digit_timeout:"Wait for further digits",max_call_duration:"Maximum call duration"},helpers:{greeting:"Spoken first. Templates are supported (caller, caller_name). Empty: no greeting.",announce_menu:"Reads out all commands and assistants. When off, a short tone signals that input is expected.",menu_prompt:"Replaces the generated announcement. Templates are supported.",pin:"Optional 4\u201312 digit PIN callers enter (followed by #) before anything else.",tts_engine:"Used for greeting, menu and confirmations. Empty: preferred engine.",language:"Language of announcements and assistants. Empty: Home Assistant language.",digit_timeout:"How long to wait before a multi-digit code is submitted. # submits immediately.",max_call_duration:"Calls are ended automatically after this time."}},connection:{sip:"SIP connection",sip_desc:"How phones reach Home Assistant. Changes restart the SIP server and end running calls.",openai:"OpenAI",openai_desc:"The API key is used by all assistants.",network:"Network and security",network_desc:"Who may call and which ports carry the audio.",fields:{sip_port:"SIP port (UDP)",sip_user:"SIP user",sip_password:"New password",clear_sip_password:"Remove the password",api_key:"New API key",clear_api_key:"Remove the API key",allowed_networks:"Allowed networks",rtp_port_start:"First RTP port",rtp_port_end:"Last RTP port",external_host:"Advertised address",max_calls:"Simultaneous calls"},helpers:{sip_port:"The built-in Voice over IP integration also uses 5060 by default.",sip_user:"User part of the SIP address and username for authentication.",password_set:"A password is set. Leave empty to keep it.",password_none:"No password: calls are accepted without authentication.",api_key_set:"Stored key: {hint}. Leave empty to keep it.",api_key_none:"No API key: assistants are disabled.",api_key_link:"Create a key at platform.openai.com/api-keys.",allowed_networks:"Comma separated networks (CIDR) that may call. Empty allows everyone.",rtp_port_start:"UDP ports for call audio, one per call.",external_host:"Only needed behind NAT: address placed in SIP and SDP headers."}}},tt={tabs:{overview:"\xDCbersicht",commands:"Tastenbefehle",assistants:"Assistenten",call:"Anrufablauf",connection:"Verbindung"},common:{save:"Speichern",saved:"Gespeichert",cancel:"\xC4nderungen verwerfen",delete:"L\xF6schen",delete_confirm:"Wirklich l\xF6schen?",back:"Zur\xFCck",loading:"Wird geladen \u2026",error_loading:"Die Konfiguration konnte nicht geladen werden.",no_entry:"SIP Assistant ist noch nicht eingerichtet. F\xFCge die Integration unter Einstellungen \u2192 Ger\xE4te & Dienste hinzu.",not_loaded:"Dieser Eintrag l\xE4uft nicht. Pr\xFCfe das Protokoll; eventuell ist der SIP-Port belegt.",unsaved:"Ungespeicherte \xC4nderungen",form_errors:"Bitte pr\xFCfe die markierten Felder.",save_failed:"Speichern fehlgeschlagen: {error}"},errors:{required:"Pflichtfeld",invalid_code:"1\u20138 Zeichen aus 0\u20139 und A\u2013D",code_in_use:"Dieser Code ist bereits vergeben",name_in_use:"Dieser Name ist bereits vergeben",invalid_entity:"Dieser Entit\xE4tstyp wird nicht unterst\xFCtzt",invalid_actions:"Die Aktionen sind ung\xFCltig",invalid_template:"Das Template ist ung\xFCltig",invalid_pin:"4\u201312 Ziffern",invalid_networks:"Keine g\xFCltige Adresse bzw. kein g\xFCltiges CIDR-Netz",invalid_rtp_range:"Der Bereich muss mindestens zwei Ports umfassen",invalid_number:"Wert au\xDFerhalb des erlaubten Bereichs",invalid_option:"Ung\xFCltige Auswahl",port_in_use:"Port ist bereits belegt",invalid_user:"Nur Buchstaben, Ziffern und . _ ~ + -",invalid_auth:"OpenAI hat den API-Key abgelehnt",cannot_connect:"OpenAI war zur Pr\xFCfung nicht erreichbar"},state:{idle:"Bereit",pin:"PIN-Eingabe",menu:"Tastenmen\xFC",assistant:"Sprachassistent",unavailable:"L\xE4uft nicht"},overview:{status:"Status",active_calls:"Aktive Anrufe",sip_address:"SIP-Adresse",copy:"Kopieren",copied:"SIP-Adresse kopiert",how_to:"W\xE4hle diese Adresse mit einem Softphone, SIP-Telefon oder Telefonadapter.",last_caller:"Letzter Anrufer",last_call:"Letzter Anruf",never:"Noch kein Anruf",hang_up:"Alle Anrufe beenden",keypad:"Tastenbelegung",keypad_hint:"Das erreichen Anrufer \xFCber die Tastatur.",starts_with:"Anrufe beginnen mit",start_menu:"dem Tastenmen\xFC",key_repeat:"Men\xFC wiederholen / zur\xFCck ins Men\xFC",key_submit:"Mehrstelligen Code abschlie\xDFen",announced:"Wird angesagt",not_announced:"Wird nicht angesagt",unreachable:"Nicht erreichbar (kein API-Key)",checks:"Hinweise",all_good:"Alles eingerichtet, keine Auff\xE4lligkeiten.",check_no_api_key:"Es sind Assistenten eingerichtet, aber kein OpenAI-API-Key hinterlegt \u2013 Anrufer erreichen sie nicht.",check_risky:"\u201E{name}\u201C kombiniert Websuche mit Zugriff auf dein Zuhause.",check_no_tts:"Keine Sprachausgabe (TTS) verf\xFCgbar \u2013 Ansagen werden durch T\xF6ne ersetzt.",check_open:"Es gibt kein SIP-Passwort und Anrufe sind aus allen Netzen erlaubt.",check_nothing:"Noch keine Tastenbefehle oder Assistenten \u2013 Anrufer h\xF6ren nur die Begr\xFC\xDFung.",go_connection:"Zur Verbindung",go_assistants:"Zu den Assistenten",go_commands:"Befehl anlegen"},commands:{add:"Neuer Befehl",empty:"Noch keine Tastenbefehle. Lege den ersten an, z. B. \u201E1\u201C f\xFCr das Garagentor.",select:"W\xE4hle einen Befehl aus oder lege einen neuen an.",new:"Neuer Tastenbefehl",type:"Was soll passieren?",type_entity:"Entit\xE4t ausf\xFChren",type_entity_desc:"Skript oder Szene starten, Automation ausl\xF6sen, Button dr\xFCcken oder Licht/Schalter umschalten.",type_actions:"Eigene Aktionen",type_actions_desc:"Beliebige Abl\xE4ufe mit dem Aktionseditor zusammenstellen.",type_announcement:"Text ansagen",type_announcement_desc:"Einen Text vorlesen, z. B. einen Sensorwert per Template.",badge_menu:"Men\xFC",badge_ai:"KI",fields:{name:"Name",code:"Tastencode",entity_id:"Entit\xE4t",actions:"Aktionen",response:"Gesprochene Best\xE4tigung",response_announcement:"Text",announce:"In der Men\xFCansage nennen",ai_enabled:"Assistenten d\xFCrfen ihn ausf\xFChren",description:"Beschreibung f\xFCr die Assistenten"},helpers:{code:"1\u20138 Zeichen aus 0\u20139 und A\u2013D. * und # sind reserviert.",entity_id:"Skripte und Szenen werden gestartet, Automationen ausgel\xF6st, Buttons gedr\xFCckt und andere Entit\xE4ten umgeschaltet.",actions:"Die Variablen caller, caller_name und code stehen zur Verf\xFCgung.",response:"Optional. Templates werden unterst\xFCtzt. Leer: \u201ENAME wurde ausgef\xFChrt\u201C.",response_announcement:"Templates werden unterst\xFCtzt, z. B. um einen Sensorzustand vorzulesen.",description:"Hilft den Assistenten zu entscheiden, wann sie den Befehl nutzen."}},assistants:{add:"Neuer Assistent",empty:"Noch keine Assistenten. Jeder Assistent hat eine eigene Taste, z. B. \u201E0\u201C mit Zugriff aufs Haus und \u201E1\u201C mit Websuche.",select:"W\xE4hle einen Assistenten aus oder lege einen neuen an.",new:"Neuer Assistent",general:"Allgemein",model:"Modell und Stimme",access:"Zugriff und Werkzeuge",behaviour:"Gespr\xE4chsverhalten",advanced:"Erweiterte Modelleinstellungen",starts_calls:"Startet Anrufe",badge_home:"Ger\xE4te",badge_commands:"Befehle",badge_web:"Websuche",badge_talk:"Nur Gespr\xE4ch",engine_live:"GPT-Live",engine_live_desc:"Vollduplexf\xE4higes Sprachmodell, das Werkzeuge an ein schnelles Backend-Modell delegiert. Die nat\xFCrlichsten Gespr\xE4che.",engine_realtime:"Realtime-API",engine_realtime_desc:"Ein einzelnes Sprach-zu-Sprach-Modell, das die Werkzeuge selbst nutzt.",home_control:"Ger\xE4te steuern",home_control_desc:"Der Assistent darf \xFCber Home Assistant Entit\xE4ten schalten und abfragen.",llm_apis:"Home-Assistant-APIs",llm_apis_desc:"\u201EAssist\u201C steuert die f\xFCr Assist freigegebenen Entit\xE4ten.",phone_commands:"Tastenbefehle ausf\xFChren",phone_commands_desc:"Tastenbefehle, die es erlauben, lassen sich auch per Sprache ausl\xF6sen.",web_search:"Websuche",web_search_desc:"Aktuelle Informationen wie Nachrichten, Wetter oder \xD6ffnungszeiten nachschlagen.",fast_interrupt:"Schnelle Unterbrechung",fast_interrupt_desc:"Stoppt den Assistenten, sobald du hineinsprichst, statt auf die Erkennung durch OpenAI zu warten. Abschalten, falls Hintergrundger\xE4usche ihn abbrechen.",risky_title:"Websuche und Zugriff auf dein Zuhause sind gleichzeitig aktiv",risky_text:"Webseiten k\xF6nnen versteckte Anweisungen enthalten (Prompt Injection), die den Assistenten zu Aktionen in deinem Zuhause verleiten. Kombiniere beides nur, wenn du das Risiko bewusst eingehst.",no_api_key:"Ohne OpenAI-API-Key ist dieser Assistent nicht erreichbar.",effort:{none:"Keiner",minimal:"Minimal",low:"Niedrig",medium:"Mittel",high:"Hoch"},fields:{name:"Name",code:"Tastencode",announce:"In der Men\xFCansage nennen",voice:"Stimme",prompt:"Anweisungen",live_model:"GPT-Live-Modell",backend_model:"Backend-Modell (GPT-Live-Werkzeuge, Websuche)",reasoning_effort:"Denkaufwand des Backends",realtime_model:"Realtime-Modell"},helpers:{code:"1\u20138 Zeichen aus 0\u20139 und A\u2013D. * und # sind reserviert.",voice:"GPT-Live kennt weitere Stimmen, die per Name eingegeben werden k\xF6nnen.",prompt:"Pers\xF6nlichkeit und Verhalten. Leer: Standardanweisungen. Templates werden unterst\xFCtzt.",reasoning_effort:"Niedrigere Werte antworten schneller."}},call:{title:"Anrufablauf",description:"Was Anrufer h\xF6ren und wie sich das Tastenmen\xFC verh\xE4lt.",start_menu:"Tastenmen\xFC",fields:{start:"Nach dem Annehmen beginnen mit",greeting:"Begr\xFC\xDFung",announce_menu:"Men\xFC ansagen",menu_prompt:"Eigene Men\xFCansage",pin:"PIN",tts_engine:"Sprachausgabe (TTS)",language:"Sprache",digit_timeout:"Auf weitere Ziffern warten",max_call_duration:"Maximale Gespr\xE4chsdauer"},helpers:{greeting:"Wird zuerst gesprochen. Templates werden unterst\xFCtzt (caller, caller_name). Leer: keine Begr\xFC\xDFung.",announce_menu:"Liest alle Befehle und Assistenten vor. Ist das aus, signalisiert ein kurzer Ton die Eingabebereitschaft.",menu_prompt:"Ersetzt die automatisch erzeugte Ansage. Templates werden unterst\xFCtzt.",pin:"Optionale 4\u201312-stellige PIN, die Anrufer zuerst eingeben (abschlie\xDFen mit #).",tts_engine:"F\xFCr Begr\xFC\xDFung, Men\xFC und Best\xE4tigungen. Leer: bevorzugte Engine.",language:"Sprache der Ansagen und Assistenten. Leer: Home-Assistant-Sprache.",digit_timeout:"Wie lange auf weitere Ziffern gewartet wird. # best\xE4tigt sofort.",max_call_duration:"Danach wird der Anruf automatisch beendet."}},connection:{sip:"SIP-Anschluss",sip_desc:"Wie Telefone Home Assistant erreichen. \xC4nderungen starten den SIP-Server neu und beenden laufende Anrufe.",openai:"OpenAI",openai_desc:"Der API-Key wird von allen Assistenten genutzt.",network:"Netzwerk und Sicherheit",network_desc:"Wer anrufen darf und \xFCber welche Ports das Audio l\xE4uft.",fields:{sip_port:"SIP-Port (UDP)",sip_user:"SIP-Benutzer",sip_password:"Neues Passwort",clear_sip_password:"Passwort entfernen",api_key:"Neuer API-Key",clear_api_key:"API-Key entfernen",allowed_networks:"Erlaubte Netzwerke",rtp_port_start:"Erster RTP-Port",rtp_port_end:"Letzter RTP-Port",external_host:"Angek\xFCndigte Adresse",max_calls:"Gleichzeitige Anrufe"},helpers:{sip_port:"Die eingebaute VoIP-Integration nutzt standardm\xE4\xDFig ebenfalls 5060.",sip_user:"Benutzerteil der SIP-Adresse und Benutzername f\xFCr die Anmeldung.",password_set:"Ein Passwort ist gesetzt. Leer lassen, um es zu behalten.",password_none:"Kein Passwort: Anrufe werden ohne Anmeldung angenommen.",api_key_set:"Gespeicherter Key: {hint}. Leer lassen, um ihn zu behalten.",api_key_none:"Kein API-Key: Assistenten sind deaktiviert.",api_key_link:"Einen Key erstellst du unter platform.openai.com/api-keys.",allowed_networks:"Kommagetrennte Netze (CIDR), aus denen angerufen werden darf. Leer erlaubt alle.",rtp_port_start:"UDP-Ports f\xFCr das Gespr\xE4chsaudio, einer pro Anruf.",external_host:"Nur hinter NAT n\xF6tig: Adresse in SIP- und SDP-Headern."}}},Ue=(a,e)=>{let t=a;for(let s of e.split(".")){if(typeof t!="object"||t===null)return;t=t[s]}return typeof t=="string"?t:void 0},de=a=>{let e=a?.toLowerCase().startsWith("de")?tt:Me;return(t,s)=>{let i=Ue(e,t)??Ue(Me,t)??t;for(let[n,r]of Object.entries(s??{}))i=i.replaceAll(`{${n}}`,String(r));return i}};var g=k`
  :host {
    display: block;
  }
  ha-card {
    display: block;
    margin-bottom: 16px;
  }
  .card-content {
    padding: 0 16px 16px;
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 16px 8px;
    font-size: 20px;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .card-subtitle {
    margin: -4px 16px 12px;
    color: var(--secondary-text-color);
    font-size: 14px;
    line-height: 1.4;
  }
  .card-actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    padding: 8px 16px;
    border-top: 1px solid var(--divider-color);
  }
  .card-actions .spacer {
    flex: 1;
  }
  .section-title {
    margin: 24px 0 4px;
    font-size: 15px;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .section-title:first-child {
    margin-top: 8px;
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .code {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    height: 36px;
    padding: 0 8px;
    box-sizing: border-box;
    border-radius: 10px;
    background: rgba(var(--rgb-primary-color), 0.14);
    color: var(--primary-color);
    font-weight: 600;
    font-size: 16px;
    font-family: var(--ha-font-family-code, monospace);
    letter-spacing: 1px;
    flex-shrink: 0;
  }
  .code.fixed {
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    line-height: 18px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .badge ha-icon {
    --mdc-icon-size: 14px;
  }
  .badge.accent {
    background: rgba(var(--rgb-primary-color), 0.14);
    color: var(--primary-color);
  }
  .badge.warning {
    background: rgba(var(--rgb-warning-color, 255, 166, 0), 0.18);
    color: var(--warning-color);
  }
  ha-alert {
    display: block;
    margin: 8px 0;
  }
  ha-form {
    display: block;
  }

  /* Master-detail layout */
  .master-detail {
    display: grid;
    grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }
  .master-detail.narrow {
    grid-template-columns: minmax(0, 1fr);
  }
  .list {
    padding: 0 0 8px;
  }
  .list-item {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 10px 16px;
    box-sizing: border-box;
    border: none;
    background: none;
    text-align: start;
    color: var(--primary-text-color);
    font: inherit;
    cursor: pointer;
    border-inline-start: 3px solid transparent;
  }
  .list-item:hover {
    background: var(--secondary-background-color);
  }
  .list-item.selected {
    background: rgba(var(--rgb-primary-color), 0.08);
    border-inline-start-color: var(--primary-color);
  }
  .list-item .text {
    flex: 1;
    min-width: 0;
  }
  .list-item .primary {
    font-size: 15px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .list-item .secondary {
    margin-top: 2px;
    font-size: 13px;
    color: var(--secondary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .list-item .badges {
    margin-top: 4px;
  }
  .empty {
    padding: 8px 16px 16px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    min-height: 240px;
    padding: 24px;
    text-align: center;
    color: var(--secondary-text-color);
  }
  .placeholder ha-icon {
    --mdc-icon-size: 48px;
    opacity: 0.5;
  }
  .editor-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 16px 8px;
  }
  .editor-header .title {
    flex: 1;
    font-size: 20px;
    font-weight: 500;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 50%;
    background: none;
    color: var(--secondary-text-color);
    cursor: pointer;
  }
  .icon-button:hover {
    background: var(--secondary-background-color);
  }

  /* Choice tiles */
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 8px;
    margin: 8px 0 16px;
  }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border: 1px solid var(--divider-color);
    border-radius: 12px;
    background: none;
    color: var(--primary-text-color);
    font: inherit;
    text-align: start;
    cursor: pointer;
  }
  .tile:hover {
    border-color: var(--primary-color);
  }
  .tile.selected {
    border-color: var(--primary-color);
    background: rgba(var(--rgb-primary-color), 0.08);
    box-shadow: inset 0 0 0 1px var(--primary-color);
  }
  .tile .tile-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
  }
  .tile .tile-title ha-icon {
    color: var(--primary-color);
  }
  .tile .tile-desc {
    font-size: 13px;
    line-height: 1.4;
    color: var(--secondary-text-color);
  }

  /* Switch rows */
  .switch-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid var(--divider-color);
  }
  .switch-row:last-child {
    border-bottom: none;
  }
  .switch-row ha-icon {
    color: var(--secondary-text-color);
    flex-shrink: 0;
  }
  .switch-row .text {
    flex: 1;
    min-width: 0;
  }
  .switch-row .heading {
    font-size: 15px;
  }
  .switch-row .description {
    margin-top: 2px;
    font-size: 13px;
    line-height: 1.4;
    color: var(--secondary-text-color);
  }
  .nested {
    padding: 0 0 8px 40px;
  }
  .unsaved {
    font-size: 13px;
    color: var(--secondary-text-color);
  }
`;var x=(a,e)=>Object.fromEntries(Object.entries(a).map(([t,s])=>[t,e(`errors.${s}`)])),f=(a,e)=>{a.dispatchEvent(new CustomEvent("config-changed",{detail:{config:e},bubbles:!0,composed:!0}))},Z=(a,e)=>{a.dispatchEvent(new CustomEvent("navigate-tab",{detail:{tab:e},bubbles:!0,composed:!0}))},C=a=>[...a].sort((e,t)=>e.code.localeCompare(t.code,void 0,{numeric:!0})),J=(a,e=1)=>{let t=new Set([...a.commands,...a.assistants].map(s=>s.code));for(let s=0;s<10;s++){let i=String((e+s)%10);if(!t.has(i))return i}for(let s=10;s<100;s++)if(!t.has(String(s)))return String(s);return""},V=a=>Array.isArray(a)?a.map(V):a&&typeof a=="object"?Object.fromEntries(Object.entries(a).filter(([,e])=>e!=null&&e!=="").sort(([e],[t])=>e.localeCompare(t)).map(([e,t])=>[e,V(t)])):a,v=(a,e)=>e===void 0||JSON.stringify(V(a))!==JSON.stringify(V(e));var st=[{engine:"live",icon:"mdi:account-voice"},{engine:"realtime",icon:"mdi:waveform"}],D=a=>a.web_search&&(a.home_control&&a.llm_hass_api.length>0||a.phone_commands),he=class extends m{static{this.properties={hass:{attribute:!1},data:{attribute:!1},localize:{attribute:!1},narrow:{type:Boolean},_selected:{state:!0},_draft:{state:!0},_errors:{state:!0},_saving:{state:!0},_confirmDelete:{state:!0}}}static{this.styles=g}constructor(){super(),this.narrow=!1,this._selected=null,this._draft=null,this._errors={},this._saving=!1,this._confirmDelete=!1}get _original(){return this.data.assistants.find(e=>e.id===this._selected)}render(){let e=!this.narrow||this._selected===null,t=!this.narrow||this._selected!==null;return o`
      <div class="master-detail ${this.narrow?"narrow":""}">
        ${e?this._renderList():l}
        ${t?this._renderEditor():l}
      </div>
    `}_badges(e){let t=e.home_control&&e.llm_hass_api.length>0;return o`
      <div class="badges">
        ${e.id===this.data.call.start?o`<span class="badge accent"
              ><ha-icon icon="mdi:phone-in-talk"></ha-icon>${this.localize("assistants.starts_calls")}</span
            >`:l}
        ${t?o`<span class="badge"
              ><ha-icon icon="mdi:home-automation"></ha-icon>${this.localize("assistants.badge_home")}</span
            >`:l}
        ${e.phone_commands?o`<span class="badge"
              ><ha-icon icon="mdi:dialpad"></ha-icon>${this.localize("assistants.badge_commands")}</span
            >`:l}
        ${e.web_search?o`<span class="badge ${D(e)?"warning":""}"
              ><ha-icon icon=${D(e)?"mdi:alert-outline":"mdi:web"}></ha-icon>${this.localize("assistants.badge_web")}</span
            >`:l}
        ${!t&&!e.phone_commands&&!e.web_search?o`<span class="badge"
              ><ha-icon icon="mdi:chat-outline"></ha-icon>${this.localize("assistants.badge_talk")}</span
            >`:l}
      </div>
    `}_renderList(){let e=C(this.data.assistants);return o`
      <ha-card>
        <div class="card-header">
          <span>${this.localize("tabs.assistants")}</span>
          <ha-button appearance="filled" size="small" @click=${this._new}>
            <ha-icon slot="start" icon="mdi:plus"></ha-icon>
            ${this.localize("assistants.add")}
          </ha-button>
        </div>
        ${!this.data.connection.has_api_key&&e.length?o`<div class="card-content">
              <ha-alert alert-type="warning">${this.localize("assistants.no_api_key")}</ha-alert>
            </div>`:l}
        <div class="list">
          ${e.length===0?o`<div class="empty">${this.localize("assistants.empty")}</div>`:e.map(t=>o`
                  <button
                    class="list-item ${t.id===this._selected?"selected":""}"
                    @click=${()=>this._select(t)}
                  >
                    <span class="code">${t.code}</span>
                    <span class="text">
                      <div class="primary">${t.name}</div>
                      <div class="secondary">
                        ${this.localize(`assistants.engine_${t.engine}`)} · ${t.voice}
                      </div>
                      ${this._badges(t)}
                    </span>
                  </button>
                `)}
        </div>
      </ha-card>
    `}_renderEditor(){if(this._draft===null)return o`
        <ha-card>
          <div class="placeholder">
            <ha-icon icon="mdi:account-voice"></ha-icon>
            <div>${this.localize("assistants.select")}</div>
          </div>
        </ha-card>
      `;let e=this._draft,t=v(e,this._original),s=x(this._errors,this.localize);return o`
      <ha-card>
        <div class="editor-header">
          ${this.narrow?o`<button class="icon-button" @click=${this._close} title=${this.localize("common.back")}>
                <ha-icon icon="mdi:arrow-left"></ha-icon>
              </button>`:l}
          <span class="code">${e.code||"?"}</span>
          <span class="title">${e.name||this.localize("assistants.new")}</span>
        </div>
        <div class="card-content">
          ${this.data.connection.has_api_key?l:o`<ha-alert alert-type="warning">
                ${this.localize("assistants.no_api_key")}
                <ha-button slot="action" appearance="plain" size="small" @click=${()=>Z(this,"connection")}
                  >${this.localize("overview.go_connection")}</ha-button
                >
              </ha-alert>`}

          <div class="section-title">${this.localize("assistants.general")}</div>
          ${this._form([{name:"name",required:!0,selector:{text:{}}},{name:"code",required:!0,selector:{text:{}}},{name:"announce",selector:{boolean:{}}}],s)}

          <div class="section-title">${this.localize("assistants.model")}</div>
          <div class="tiles">
            ${st.map(({engine:i,icon:n})=>o`
                <button
                  class="tile ${e.engine===i?"selected":""}"
                  @click=${()=>this._update({engine:i})}
                >
                  <span class="tile-title"><ha-icon .icon=${n}></ha-icon>${this.localize(`assistants.engine_${i}`)}</span>
                  <span class="tile-desc">${this.localize(`assistants.engine_${i}_desc`)}</span>
                </button>
              `)}
          </div>
          ${this._form([{name:"voice",required:!0,selector:{select:{options:this.data.info.voices,custom_value:!0,mode:"dropdown"}}},{name:"prompt",selector:{template:{}}}],s)}

          <div class="section-title">${this.localize("assistants.access")}</div>
          ${this._switch("home_control","mdi:home-automation")}
          ${e.home_control?o`<div class="nested">
                ${this._form([{name:"llm_hass_api",selector:{select:{multiple:!0,mode:"list",options:this.data.info.llm_apis.map(i=>({value:i.id,label:i.name}))}}}],s)}
              </div>`:l}
          ${this._switch("phone_commands","mdi:dialpad")} ${this._switch("web_search","mdi:web")}
          ${D(e)?o`<ha-alert alert-type="warning" .title=${this.localize("assistants.risky_title")}>
                ${this.localize("assistants.risky_text")}
              </ha-alert>`:l}

          <div class="section-title">${this.localize("assistants.behaviour")}</div>
          ${this._switch("fast_interrupt","mdi:hand-back-left-outline")}

          <ha-expansion-panel outlined .header=${this.localize("assistants.advanced")}>
            ${this._form(e.engine==="live"?[this._modelField("live_model",this.data.info.live_models),this._modelField("backend_model",this.data.info.backend_models),{name:"reasoning_effort",selector:{select:{mode:"dropdown",options:this.data.info.reasoning_efforts.map(i=>({value:i,label:this.localize(`assistants.effort.${i}`)}))}}}]:[this._modelField("realtime_model",this.data.info.realtime_models),this._modelField("backend_model",this.data.info.backend_models)],s)}
          </ha-expansion-panel>
        </div>
        <div class="card-actions">
          ${this._selected!=="new"?o`<ha-button
                variant="danger"
                appearance=${this._confirmDelete?"filled":"plain"}
                @click=${this._delete}
                >${this.localize(this._confirmDelete?"common.delete_confirm":"common.delete")}</ha-button
              >`:l}
          <span class="spacer"></span>
          ${t?o`<ha-button appearance="plain" @click=${this._discard}
                >${this.localize("common.cancel")}</ha-button
              >`:l}
          <ha-button
            appearance="filled"
            .disabled=${!t||this._saving}
            .loading=${this._saving}
            @click=${this._save}
            >${this.localize("common.save")}</ha-button
          >
        </div>
      </ha-card>
    `}_modelField(e,t){return{name:e,required:!0,selector:{select:{options:t,custom_value:!0,mode:"dropdown"}}}}_form(e,t){return o`<ha-form
      .hass=${this.hass}
      .data=${this._draft}
      .schema=${e}
      .error=${t}
      .computeLabel=${s=>s.name==="llm_hass_api"?this.localize("assistants.llm_apis"):this.localize(`assistants.fields.${s.name}`)}
      .computeHelper=${s=>{if(s.name==="llm_hass_api")return this.localize("assistants.llm_apis_desc");let i=`assistants.helpers.${s.name}`,n=this.localize(i);return n===i?void 0:n}}
      @value-changed=${s=>this._update(s.detail.value)}
    ></ha-form>`}_switch(e,t){return o`
      <div class="switch-row">
        <ha-icon .icon=${t}></ha-icon>
        <div class="text">
          <div class="heading">${this.localize(`assistants.${e}`)}</div>
          <div class="description">${this.localize(`assistants.${e}_desc`)}</div>
        </div>
        <ha-switch
          .checked=${this._draft[e]}
          @change=${s=>this._update({[e]:s.target.checked})}
        ></ha-switch>
      </div>
    `}_select(e){this._selected=e.id??null,this._draft=structuredClone(e),this._errors={},this._confirmDelete=!1}_new(){let e=this.data.info;this._selected="new",this._draft={name:"",code:J(this.data,0),engine:"live",voice:e.voices[0]??"marin",prompt:"",home_control:!1,llm_hass_api:e.llm_apis.some(t=>t.id==="assist")?["assist"]:[],phone_commands:!1,web_search:!1,fast_interrupt:!0,announce:!0,live_model:e.live_models[0],backend_model:e.backend_models[0],reasoning_effort:"low",realtime_model:e.realtime_models[0]},this._errors={},this._confirmDelete=!1}_close(){this._selected=null,this._draft=null}_discard(){let e=this._original;e?this._select(e):this._close()}_update(e){this._draft!==null&&(this._draft={...this._draft,...e},this._confirmDelete=!1)}async _save(){if(this._draft!==null){this._saving=!0;try{let e=await q(this.hass,this.data.entry_id,"assistant",this._draft);if(e.errors){this._errors=e.errors,u(this,this.localize("common.form_errors"));return}this._errors={};let t=e.config,s=t.assistants.find(i=>i.id===this._draft.id)??t.assistants.find(i=>i.code===this._draft.code.toUpperCase());f(this,t),s&&(this._selected=s.id??null,this._draft=structuredClone(s)),u(this,this.localize("common.saved"))}catch(e){u(this,this.localize("common.save_failed",{error:e?.message??String(e)}))}finally{this._saving=!1}}}async _delete(){if(!this._confirmDelete){this._confirmDelete=!0;return}if(!this._selected||this._selected==="new")return;let e=await G(this.hass,this.data.entry_id,"assistant",this._selected);e.config&&f(this,e.config),this._close(),this._confirmDelete=!1}};customElements.get("sip-assistant-assistants")||customElements.define("sip-assistant-assistants",he);var pe={start:"menu",greeting:"",announce_menu:!0,menu_prompt:"",pin:"",tts_engine:"",language:"",digit_timeout:3,max_call_duration:15},me=class extends m{static{this.properties={hass:{attribute:!1},data:{attribute:!1},localize:{attribute:!1},narrow:{type:Boolean},_draft:{state:!0},_errors:{state:!0},_saving:{state:!0}}}static{this.styles=g}constructor(){super(),this.narrow=!1,this._draft={...pe},this._errors={},this._saving=!1}get _original(){return{...pe,...this.data.call}}willUpdate(e){e.has("data")&&(!e.get("data")||!v(this._draft,e.get("data")?.call))&&(this._draft=this._original)}_schema(){return[{name:"start",required:!0,selector:{select:{mode:"dropdown",options:[{value:"menu",label:this.localize("call.start_menu")},...this.data.assistants.map(e=>({value:e.id,label:`${e.name} (${e.code})`}))]}}},{name:"greeting",selector:{template:{}}},{name:"announce_menu",selector:{boolean:{}}},{name:"menu_prompt",selector:{template:{}}},{name:"pin",selector:{text:{type:"password",autocomplete:"off"}}},{name:"tts_engine",selector:{entity:{filter:{domain:"tts"}}}},{name:"language",selector:{language:{}}},{name:"digit_timeout",required:!0,selector:{number:{min:1,max:10,step:.5,mode:"slider",unit_of_measurement:"s"}}},{name:"max_call_duration",required:!0,selector:{number:{min:1,max:120,step:1,mode:"box",unit_of_measurement:"min"}}}]}render(){let e=v(this._draft,this._original);return o`
      <ha-card>
        <div class="card-header">${this.localize("call.title")}</div>
        <div class="card-subtitle">${this.localize("call.description")}</div>
        <div class="card-content">
          <ha-form
            .hass=${this.hass}
            .data=${this._draft}
            .schema=${this._schema()}
            .error=${x(this._errors,this.localize)}
            .computeLabel=${t=>this.localize(`call.fields.${t.name}`)}
            .computeHelper=${t=>{let s=`call.helpers.${t.name}`,i=this.localize(s);return i===s?void 0:i}}
            @value-changed=${t=>{this._draft={...this._draft,...t.detail.value}}}
          ></ha-form>
        </div>
        <div class="card-actions">
          ${e?o`<ha-button appearance="plain" @click=${()=>this._draft=this._original}
                >${this.localize("common.cancel")}</ha-button
              >`:""}
          <ha-button
            appearance="filled"
            .disabled=${!e||this._saving}
            .loading=${this._saving}
            @click=${this._save}
            >${this.localize("common.save")}</ha-button
          >
        </div>
      </ha-card>
    `}async _save(){this._saving=!0;try{let e=await j(this.hass,this.data.entry_id,"call",{...this._draft});if(e.errors){this._errors=e.errors,u(this,this.localize("common.form_errors"));return}this._errors={},this._draft={...pe,...e.config.call},f(this,e.config),u(this,this.localize("common.saved"))}catch(e){u(this,this.localize("common.save_failed",{error:e?.message??String(e)}))}finally{this._saving=!1}}};customElements.get("sip-assistant-call-flow")||customElements.define("sip-assistant-call-flow",me);var it=[{type:"entity",icon:"mdi:play-circle-outline"},{type:"actions",icon:"mdi:format-list-bulleted-square"},{type:"announcement",icon:"mdi:account-voice"}],ue=class extends m{static{this.properties={hass:{attribute:!1},data:{attribute:!1},localize:{attribute:!1},narrow:{type:Boolean},_selected:{state:!0},_draft:{state:!0},_errors:{state:!0},_saving:{state:!0},_confirmDelete:{state:!0}}}static{this.styles=g}constructor(){super(),this.narrow=!1,this._selected=null,this._draft=null,this._errors={},this._saving=!1,this._confirmDelete=!1}get _original(){return this.data.commands.find(e=>e.id===this._selected)}render(){let e=!this.narrow||this._selected===null,t=!this.narrow||this._selected!==null;return o`
      <div class="master-detail ${this.narrow?"narrow":""}">
        ${e?this._renderList():l}
        ${t?this._renderEditor():l}
      </div>
    `}_renderList(){let e=C(this.data.commands);return o`
      <ha-card>
        <div class="card-header">
          <span>${this.localize("tabs.commands")}</span>
          <ha-button appearance="filled" size="small" @click=${this._new}>
            <ha-icon slot="start" icon="mdi:plus"></ha-icon>
            ${this.localize("commands.add")}
          </ha-button>
        </div>
        <div class="list">
          ${e.length===0?o`<div class="empty">${this.localize("commands.empty")}</div>`:e.map(t=>o`
                  <button
                    class="list-item ${t.id===this._selected?"selected":""}"
                    @click=${()=>this._select(t)}
                  >
                    <span class="code">${t.code}</span>
                    <span class="text">
                      <div class="primary">${t.name}</div>
                      <div class="secondary">${this._describe(t)}</div>
                      <div class="badges">
                        ${t.announce?o`<span class="badge"
                              ><ha-icon icon="mdi:bullhorn-outline"></ha-icon>${this.localize("commands.badge_menu")}</span
                            >`:l}
                        ${t.ai_enabled?o`<span class="badge accent"
                              ><ha-icon icon="mdi:robot-outline"></ha-icon>${this.localize("commands.badge_ai")}</span
                            >`:l}
                      </div>
                    </span>
                  </button>
                `)}
        </div>
      </ha-card>
    `}_describe(e){switch(e.action_type){case"entity":return(e.entity_id?this.hass.states[e.entity_id]:void 0)?.attributes.friendly_name??e.entity_id??"";case"actions":return`${this.localize("commands.type_actions")} (${e.actions?.length??0})`;default:return e.response??""}}_renderEditor(){if(this._draft===null)return o`
        <ha-card>
          <div class="placeholder">
            <ha-icon icon="mdi:dialpad"></ha-icon>
            <div>${this.localize("commands.select")}</div>
          </div>
        </ha-card>
      `;let e=this._draft,t=v(e,this._original);return o`
      <ha-card>
        <div class="editor-header">
          ${this.narrow?o`<button class="icon-button" @click=${this._close} title=${this.localize("common.back")}>
                <ha-icon icon="mdi:arrow-left"></ha-icon>
              </button>`:l}
          <span class="code">${e.code||"?"}</span>
          <span class="title">${e.name||this.localize("commands.new")}</span>
        </div>
        <div class="card-content">
          <div class="section-title">${this.localize("commands.type")}</div>
          <div class="tiles">
            ${it.map(({type:s,icon:i})=>o`
                <button
                  class="tile ${e.action_type===s?"selected":""}"
                  @click=${()=>this._update({action_type:s})}
                >
                  <span class="tile-title"><ha-icon .icon=${i}></ha-icon>${this.localize(`commands.type_${s}`)}</span>
                  <span class="tile-desc">${this.localize(`commands.type_${s}_desc`)}</span>
                </button>
              `)}
          </div>
          <ha-form
            .hass=${this.hass}
            .data=${e}
            .schema=${this._schema(e.action_type)}
            .error=${x(this._errors,this.localize)}
            .computeLabel=${s=>this._label(s,e.action_type)}
            .computeHelper=${s=>this._helper(s,e.action_type)}
            @value-changed=${s=>this._update(s.detail.value)}
          ></ha-form>
        </div>
        <div class="card-actions">
          ${this._selected!=="new"?o`<ha-button
                variant="danger"
                appearance=${this._confirmDelete?"filled":"plain"}
                @click=${this._delete}
                >${this.localize(this._confirmDelete?"common.delete_confirm":"common.delete")}</ha-button
              >`:l}
          <span class="spacer"></span>
          ${t?o`<ha-button appearance="plain" @click=${this._discard}
                >${this.localize("common.cancel")}</ha-button
              >`:l}
          <ha-button
            appearance="filled"
            .disabled=${!t||this._saving}
            .loading=${this._saving}
            @click=${this._save}
            >${this.localize("common.save")}</ha-button
          >
        </div>
      </ha-card>
    `}_schema(e){let t=[{name:"name",required:!0,selector:{text:{}}},{name:"code",required:!0,selector:{text:{}}}];return e==="entity"&&t.push({name:"entity_id",required:!0,selector:{entity:{filter:{domain:this.data.info.entity_domains}}}}),e==="actions"&&t.push({name:"actions",required:!0,selector:{action:{}}}),t.push({name:"response",required:e==="announcement",selector:{template:{}}},{name:"announce",selector:{boolean:{}}},{name:"ai_enabled",selector:{boolean:{}}},{name:"description",selector:{text:{}}}),t}_label(e,t){let s=e.name==="response"&&t==="announcement"?"response_announcement":e.name;return this.localize(`commands.fields.${s}`)}_helper(e,t){let i=`commands.helpers.${e.name==="response"&&t==="announcement"?"response_announcement":e.name}`,n=this.localize(i);return n===i?void 0:n}_select(e){this._selected=e.id??null,this._draft=structuredClone(e),this._errors={},this._confirmDelete=!1}_new(){this._selected="new",this._draft={name:"",code:J(this.data),action_type:"entity",entity_id:"",response:"",announce:!0,ai_enabled:!0,description:""},this._errors={},this._confirmDelete=!1}_close(){this._selected=null,this._draft=null}_discard(){let e=this._original;e?this._select(e):this._close()}_update(e){if(this._draft===null)return;let t={...this._draft,...e};e.action_type==="announcement"&&this._draft.action_type!=="announcement"&&(t.ai_enabled=!1),this._draft=t,this._confirmDelete=!1}async _save(){if(this._draft!==null){this._saving=!0;try{let e=await q(this.hass,this.data.entry_id,"command",this._draft);if(e.errors){this._errors=e.errors,u(this,this.localize("common.form_errors"));return}this._errors={};let t=e.config,s=t.commands.find(i=>i.id===this._draft.id)??t.commands.find(i=>i.code===this._draft.code.toUpperCase());f(this,t),s&&(this._selected=s.id??null,this._draft=structuredClone(s)),u(this,this.localize("common.saved"))}catch(e){u(this,this.localize("common.save_failed",{error:e?.message??String(e)}))}finally{this._saving=!1}}}async _delete(){if(!this._confirmDelete){this._confirmDelete=!0;return}if(!this._selected||this._selected==="new")return;let e=await G(this.hass,this.data.entry_id,"command",this._selected);e.config&&f(this,e.config),this._close(),this._confirmDelete=!1}};customElements.get("sip-assistant-commands")||customElements.define("sip-assistant-commands",ue);var at={allowed_networks:"",rtp_port_start:1e4,rtp_port_end:10100,external_host:"",max_calls:2},_e=class extends m{static{this.properties={hass:{attribute:!1},data:{attribute:!1},localize:{attribute:!1},narrow:{type:Boolean},_sip:{state:!0},_key:{state:!0},_network:{state:!0},_errors:{state:!0},_saving:{state:!0}}}static{this.styles=g}constructor(){super(),this.narrow=!1,this._errors={},this._saving=null}get _sipOriginal(){return{sip_port:this.data.connection.sip_port,sip_user:this.data.connection.sip_user,sip_password:"",clear_sip_password:!1}}get _networkOriginal(){return{...at,...this.data.network}}willUpdate(e){e.has("data")&&(this._sip=this._sipOriginal,this._key={api_key:"",clear_api_key:!1},this._network=this._networkOriginal)}render(){let e=this.data.connection,t=x(this._errors,this.localize),s=v(this._sip,this._sipOriginal),i=this._key.api_key!==""||this._key.clear_api_key,n=v(this._network,this._networkOriginal);return o`
      <ha-card>
        <div class="card-header">${this.localize("connection.sip")}</div>
        <div class="card-subtitle">${this.localize("connection.sip_desc")}</div>
        <div class="card-content">
          ${this._form(this._sip,[{name:"sip_port",required:!0,selector:{number:{min:1,max:65535,mode:"box"}}},{name:"sip_user",required:!0,selector:{text:{}}},{name:"sip_password",selector:{text:{type:"password",autocomplete:"new-password"}}},...e.has_sip_password?[{name:"clear_sip_password",selector:{boolean:{}}}]:[]],t,r=>this._sip={...this._sip,...r},r=>r==="sip_password"?this.localize(e.has_sip_password?"connection.helpers.password_set":"connection.helpers.password_none"):void 0)}
        </div>
        ${this._actions("sip",s,()=>this._sip=this._sipOriginal)}
      </ha-card>

      <ha-card>
        <div class="card-header">${this.localize("connection.openai")}</div>
        <div class="card-subtitle">${this.localize("connection.openai_desc")}</div>
        <div class="card-content">
          ${e.has_api_key?l:o`<ha-alert alert-type="info">${this.localize("connection.helpers.api_key_link")}</ha-alert>`}
          ${this._form(this._key,[{name:"api_key",selector:{text:{type:"password",autocomplete:"off"}}},...e.has_api_key?[{name:"clear_api_key",selector:{boolean:{}}}]:[]],t,r=>this._key={...this._key,...r},r=>r==="api_key"?e.has_api_key?this.localize("connection.helpers.api_key_set",{hint:e.api_key_hint}):this.localize("connection.helpers.api_key_none"):void 0)}
        </div>
        ${this._actions("key",i,()=>this._key={api_key:"",clear_api_key:!1})}
      </ha-card>

      <ha-card>
        <div class="card-header">${this.localize("connection.network")}</div>
        <div class="card-subtitle">${this.localize("connection.network_desc")}</div>
        <div class="card-content">
          ${this._form(this._network,[{name:"allowed_networks",selector:{text:{}}},{name:"rtp_port_start",required:!0,selector:{number:{min:1024,max:65535,mode:"box"}}},{name:"rtp_port_end",required:!0,selector:{number:{min:1024,max:65535,mode:"box"}}},{name:"external_host",selector:{text:{}}},{name:"max_calls",required:!0,selector:{number:{min:1,max:10,mode:"box"}}}],t,r=>this._network={...this._network,...r},r=>{let d=`connection.helpers.${r}`,c=this.localize(d);return c===d?void 0:c})}
        </div>
        ${this._actions("network",n,()=>this._network=this._networkOriginal)}
      </ha-card>
    `}_form(e,t,s,i,n){return o`<ha-form
      .hass=${this.hass}
      .data=${e}
      .schema=${t}
      .error=${s}
      .computeLabel=${r=>this.localize(`connection.fields.${r.name}`)}
      .computeHelper=${r=>n(r.name)}
      @value-changed=${r=>i(r.detail.value)}
    ></ha-form>`}_actions(e,t,s){return o`
      <div class="card-actions">
        ${t?o`<ha-button appearance="plain" @click=${s}>${this.localize("common.cancel")}</ha-button>`:l}
        <ha-button
          appearance="filled"
          .disabled=${!t||this._saving!==null}
          .loading=${this._saving===e}
          @click=${()=>this._save(e)}
          >${this.localize("common.save")}</ha-button
        >
      </div>
    `}async _save(e){let t="connection",s;e==="network"?(t="network",s={...this._network}):(s={sip_port:this._sip.sip_port,sip_user:this._sip.sip_user},e==="sip"?this._sip.clear_sip_password?s.sip_password="":this._sip.sip_password&&(s.sip_password=this._sip.sip_password):(s.sip_port=this.data.connection.sip_port,s.sip_user=this.data.connection.sip_user,this._key.clear_api_key?s.api_key="":this._key.api_key&&(s.api_key=this._key.api_key))),this._saving=e;try{let i=await j(this.hass,this.data.entry_id,t,s);if(i.errors){this._errors=i.errors,u(this,this.localize("common.form_errors"));return}this._errors={},f(this,i.config),u(this,this.localize("common.saved"))}catch(i){u(this,this.localize("common.save_failed",{error:i?.message??String(i)}))}finally{this._saving=null}}};customElements.get("sip-assistant-connection")||customElements.define("sip-assistant-connection",_e);var nt={entity:"mdi:play-circle-outline",actions:"mdi:format-list-bulleted-square",announcement:"mdi:account-voice"},ge=class extends m{static{this.properties={hass:{attribute:!1},data:{attribute:!1},localize:{attribute:!1},narrow:{type:Boolean}}}static{this.styles=[g,k`
      .grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 16px;
        align-items: start;
      }
      .grid.narrow {
        grid-template-columns: minmax(0, 1fr);
      }
      .status {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 8px 16px 16px;
      }
      .status-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: rgba(var(--rgb-primary-color), 0.14);
        color: var(--primary-color);
        flex-shrink: 0;
      }
      .status-icon.busy {
        background: rgba(var(--rgb-success-color, 67, 160, 71), 0.18);
        color: var(--success-color);
      }
      .status-icon.down {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color);
      }
      .status-icon ha-icon {
        --mdc-icon-size: 28px;
      }
      .status-text .state {
        font-size: 22px;
        font-weight: 500;
      }
      .status-text .detail {
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .facts {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 8px 16px;
        padding: 0 16px 16px;
        align-items: center;
      }
      .facts .label {
        color: var(--secondary-text-color);
      }
      .uri {
        display: flex;
        align-items: center;
        gap: 4px;
        min-width: 0;
      }
      .uri code {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 15px;
        user-select: all;
      }
      .keypad-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 16px;
      }
      .keypad-row ha-icon.type {
        color: var(--secondary-text-color);
        --mdc-icon-size: 20px;
      }
      .keypad-row .text {
        flex: 1;
        min-width: 0;
      }
      .keypad-row .name {
        font-size: 15px;
      }
      .keypad-row .detail {
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .keypad-row.unreachable {
        opacity: 0.55;
      }
      .start {
        margin: 0 16px 8px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--secondary-background-color);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .divider {
        height: 1px;
        margin: 8px 16px;
        background: var(--divider-color);
      }
    `]}render(){return o`
      <div class="grid ${this.narrow?"narrow":""}">
        <div>${this._renderStatus()} ${this._renderChecks()}</div>
        <div>${this._renderKeypad()}</div>
      </div>
    `}_state(e){let t=this.data.info.entities[e];return t?this.hass.states[t]:void 0}_renderStatus(){let e=this._state("call_state"),t=this.data.loaded&&e!==void 0&&e.state!=="unavailable",s=t?e.state:"unavailable",i=Number(e?.attributes.active_calls??0),n=this._state("last_caller"),r=this._state("last_call"),d=this.data.info.sip_uri,c=t?i?"mdi:phone-in-talk":"mdi:phone-check":"mdi:phone-off";return o`
      <ha-card>
        <div class="card-header">${this.localize("overview.status")}</div>
        <div class="status">
          <div class="status-icon ${t?i?"busy":"":"down"}">
            <ha-icon .icon=${c}></ha-icon>
          </div>
          <div class="status-text">
            <div class="state">${this.localize(`state.${s}`)}</div>
            <div class="detail">
              ${i?o`${this.localize("overview.active_calls")}: ${i}
                  ${e?.attributes.caller_name||e?.attributes.caller||""}`:this.localize("overview.how_to")}
            </div>
          </div>
        </div>
        <div class="facts">
          <span class="label">${this.localize("overview.sip_address")}</span>
          <span class="uri">
            <code>${d??"\u2013"}</code>
            ${d?o`<button class="icon-button" title=${this.localize("overview.copy")} @click=${this._copy}>
                  <ha-icon icon="mdi:content-copy"></ha-icon>
                </button>`:l}
          </span>
          <span class="label">${this.localize("overview.last_caller")}</span>
          <span>${n&&n.state!=="unknown"?n.state:this.localize("overview.never")}</span>
          <span class="label">${this.localize("overview.last_call")}</span>
          <span>${r&&r.state!=="unknown"?this._formatTime(r.state):"\u2013"}</span>
        </div>
        ${i?o`<div class="card-actions">
              <ha-button variant="danger" appearance="filled" @click=${this._hangUp}>
                <ha-icon slot="start" icon="mdi:phone-hangup"></ha-icon>
                ${this.localize("overview.hang_up")}
              </ha-button>
            </div>`:l}
      </ha-card>
    `}_checks(){let e=[],{data:t}=this;t.loaded||e.push({type:"error",text:this.localize("common.not_loaded")}),t.assistants.length&&!t.connection.has_api_key&&e.push({type:"warning",text:this.localize("overview.check_no_api_key"),tab:"connection",action:"overview.go_connection"});for(let s of t.assistants.filter(D))e.push({type:"warning",text:this.localize("overview.check_risky",{name:s.name}),tab:"assistants",action:"overview.go_assistants"});return!t.connection.has_sip_password&&!t.network.allowed_networks?.trim()&&e.push({type:"warning",text:this.localize("overview.check_open"),tab:"connection",action:"overview.go_connection"}),t.loaded&&!t.info.tts_engine&&e.push({type:"info",text:this.localize("overview.check_no_tts")}),!t.commands.length&&!t.assistants.length&&e.push({type:"info",text:this.localize("overview.check_nothing"),tab:"commands",action:"overview.go_commands"}),e}_renderChecks(){let e=this._checks();return o`
      <ha-card>
        <div class="card-header">${this.localize("overview.checks")}</div>
        <div class="card-content">
          ${e.length===0?o`<ha-alert alert-type="success">${this.localize("overview.all_good")}</ha-alert>`:e.map(t=>o`<ha-alert .alertType=${t.type}>
                  ${t.text}
                  ${t.tab?o`<ha-button
                        slot="action"
                        appearance="plain"
                        size="small"
                        @click=${()=>Z(this,t.tab)}
                        >${this.localize(t.action)}</ha-button
                      >`:l}
                </ha-alert>`)}
        </div>
      </ha-card>
    `}_renderKeypad(){let{data:e}=this,t=e.assistants.find(i=>i.id===e.call.start),s=C([...e.commands,...e.assistants]);return o`
      <ha-card>
        <div class="card-header">${this.localize("overview.keypad")}</div>
        <div class="card-subtitle">${this.localize("overview.keypad_hint")}</div>
        <div class="start">
          <ha-icon icon="mdi:phone-incoming"></ha-icon>
          <span>${this.localize("overview.starts_with")} <b>${t?t.name:this.localize("overview.start_menu")}</b></span>
        </div>
        ${s.map(i=>this._renderKey(i))}
        <div class="divider"></div>
        <div class="keypad-row">
          <span class="code fixed">*</span>
          <span class="text"><div class="name">${this.localize("overview.key_repeat")}</div></span>
        </div>
        <div class="keypad-row">
          <span class="code fixed">#</span>
          <span class="text"><div class="name">${this.localize("overview.key_submit")}</div></span>
        </div>
        <div style="height: 8px"></div>
      </ha-card>
    `}_renderKey(e){let t="engine"in e,s=t&&!this.data.connection.has_api_key,i=t?"mdi:account-voice":nt[e.action_type],n=t?this.localize(`assistants.engine_${e.engine}`):this.localize(`commands.type_${e.action_type}`);return o`
      <div class="keypad-row ${s?"unreachable":""}">
        <span class="code">${e.code}</span>
        <ha-icon class="type" .icon=${i}></ha-icon>
        <span class="text">
          <div class="name">${e.name}</div>
          <div class="detail">
            ${n} ·
            ${s?this.localize("overview.unreachable"):this.localize(e.announce?"overview.announced":"overview.not_announced")}
          </div>
        </span>
        ${t&&D(e)?o`<ha-icon icon="mdi:alert-outline" style="color: var(--warning-color)"></ha-icon>`:l}
      </div>
    `}_formatTime(e){let t=new Date(e);return Number.isNaN(t.getTime())?e:t.toLocaleString(this.hass.locale?.language??this.hass.language,{dateStyle:"medium",timeStyle:"short"})}async _copy(){this.data.info.sip_uri&&(await He(this.data.info.sip_uri),u(this,this.localize("overview.copied")))}async _hangUp(){let e=this.data.info.entities.hang_up;e&&await this.hass.callService("button","press",{entity_id:e})}};customElements.get("sip-assistant-overview")||customElements.define("sip-assistant-overview",ge);var Be=[{id:"overview",icon:"mdi:view-dashboard-outline"},{id:"commands",icon:"mdi:dialpad"},{id:"assistants",icon:"mdi:account-voice"},{id:"call",icon:"mdi:phone-settings-outline"},{id:"connection",icon:"mdi:lan-connect"}],fe=class extends m{constructor(){super();this._localize=de("en");this._language="";this._entryId=new URLSearchParams(window.location.search).get("config_entry")??void 0;this.narrow=!1,this._data=null,this._error=null,this._loading=!0}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1},_data:{state:!0},_error:{state:!0},_loading:{state:!0}}}get _tab(){let t=this.route?.path?.split("/")[1]??"";return Be.find(s=>s.id===t)?.id??"overview"}willUpdate(t){if(t.has("hass")&&this.hass){let s=this.hass.locale?.language??this.hass.language;s!==this._language&&(this._language=s,this._localize=de(s)),t.get("hass")||this._load()}t.has("route")&&t.get("route")&&this._tab==="overview"&&this.hass&&this._load()}async _load(){try{this._data=await Le(this.hass,this._entryId),this._entryId=this._data?.entry_id,this._error=null}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}}_goTo(t){let s=`/${this.panel?.url_path??"sip-assistant"}`;Oe(t==="overview"?s:`${s}/${t}`)}render(){let t=this._localize;return o`
      <div class="header">
        <div class="toolbar">
          <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
          <div class="main-title">${this.panel?.title??"SIP Assistant"}</div>
          ${this._data&&this._data.entries.length>1?o`<select class="entry-select" @change=${this._entryChanged}>
                ${this._data.entries.map(s=>o`<option value=${s.entry_id} ?selected=${s.entry_id===this._data.entry_id}>
                      ${s.title}
                    </option>`)}
              </select>`:l}
        </div>
        ${this._data?o`<nav class="tabs" role="tablist">
              ${Be.map(s=>o`
                  <button
                    role="tab"
                    class="tab ${s.id===this._tab?"active":""}"
                    aria-selected=${s.id===this._tab}
                    @click=${()=>this._goTo(s.id)}
                  >
                    <ha-icon .icon=${s.icon}></ha-icon>
                    <span>${t(`tabs.${s.id}`)}</span>
                  </button>
                `)}
            </nav>`:l}
      </div>
      <div
        class="content ${this.narrow?"narrow":""}"
        @config-changed=${s=>this._data=s.detail.config}
        @navigate-tab=${s=>this._goTo(s.detail.tab)}
      >
        ${this._renderContent()}
      </div>
    `}_renderContent(){let t=this._localize;if(this._loading)return o`<div class="message"><ha-spinner></ha-spinner>${t("common.loading")}</div>`;if(this._error)return o`<ha-alert alert-type="error" .title=${t("common.error_loading")}>${this._error}</ha-alert>`;if(!this._data)return o`<ha-alert alert-type="info">${t("common.no_entry")}</ha-alert>`;let s={hass:this.hass,data:this._data,localize:t,narrow:this.narrow};switch(this._tab){case"commands":return o`<sip-assistant-commands
          .hass=${s.hass}
          .data=${s.data}
          .localize=${t}
          .narrow=${s.narrow}
        ></sip-assistant-commands>`;case"assistants":return o`<sip-assistant-assistants
          .hass=${s.hass}
          .data=${s.data}
          .localize=${t}
          .narrow=${s.narrow}
        ></sip-assistant-assistants>`;case"call":return o`<sip-assistant-call-flow
          .hass=${s.hass}
          .data=${s.data}
          .localize=${t}
          .narrow=${s.narrow}
        ></sip-assistant-call-flow>`;case"connection":return o`<sip-assistant-connection
          .hass=${s.hass}
          .data=${s.data}
          .localize=${t}
          .narrow=${s.narrow}
        ></sip-assistant-connection>`;default:return o`<sip-assistant-overview
          .hass=${s.hass}
          .data=${s.data}
          .localize=${t}
          .narrow=${s.narrow}
        ></sip-assistant-overview>`}}async _entryChanged(t){this._entryId=t.target.value,this._loading=!0,await this._load()}static{this.styles=k`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--ha-font-family-body, Roboto, sans-serif);
    }
    .header {
      position: sticky;
      top: 0;
      z-index: 4;
      background: var(--app-header-background-color);
      color: var(--app-header-text-color, white);
      border-bottom: var(--app-header-border-bottom, none);
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      height: var(--header-height, 56px);
      padding: 0 12px;
      box-sizing: border-box;
    }
    .main-title {
      flex: 1;
      margin-inline-start: 8px;
      font-size: 20px;
      font-weight: 400;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .entry-select {
      max-width: 40%;
      padding: 6px 8px;
      border-radius: 8px;
      border: 1px solid currentColor;
      background: transparent;
      color: inherit;
      font: inherit;
    }
    .entry-select option {
      color: var(--primary-text-color);
      background: var(--card-background-color);
    }
    .tabs {
      display: flex;
      gap: 4px;
      padding: 0 8px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .tab {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px 12px;
      border: none;
      border-bottom: 2px solid transparent;
      background: none;
      color: inherit;
      opacity: 0.75;
      font: inherit;
      font-size: 14px;
      font-weight: 500;
      white-space: nowrap;
      cursor: pointer;
    }
    .tab ha-icon {
      --mdc-icon-size: 20px;
    }
    .tab:hover {
      opacity: 1;
    }
    .tab.active {
      opacity: 1;
      border-bottom-color: currentColor;
    }
    .content {
      max-width: 1240px;
      margin: 0 auto;
      padding: 16px;
      box-sizing: border-box;
    }
    .content.narrow {
      padding: 8px;
    }
    .message {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 48px;
      color: var(--secondary-text-color);
    }
  `}};customElements.get("sip-assistant-panel")||customElements.define("sip-assistant-panel",fe);
