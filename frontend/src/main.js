import { createApp } from 'vue'
import { register } from 'vue-advanced-chat'
import App from './App.vue'

register()

createApp(App).mount('#app')
