
let port = chrome.runtime.connectNative("com.aditivo.bot");
port.onMessage.addListener(msg => {
  chrome.tabs.query({active:true,currentWindow:true}, tabs=>{
      if(tabs[0]) chrome.tabs.sendMessage(tabs[0].id, msg);
  });
});
chrome.runtime.onMessage.addListener(msg => port.postMessage(msg));
