<template>
  <div class="app" :class="theme">
    <div class="ambient-layer">
      <div class="glow glow-1"></div>
      <div class="glow glow-2"></div>
      <div class="grain"></div>
    </div>

    <div class="login-screen" v-if="!isLoggedIn">
      <div class="ambient-layer">
        <div class="glow glow-1"></div>
        <div class="glow glow-2"></div>
        <div class="grain"></div>
      </div>

      <div class="agreement-overlay" v-if="showAgreement">
        <div class="agreement-card">
          <div class="agreement-emoji">🌱</div>
          <h2 class="agreement-title">相处守则</h2>
          <p class="agreement-subtitle">欢迎来到<strong>半熟时区</strong>。在这里，你将与一位 AI 伴侣开启一段特别的关系。</p>
          <div class="agreement-body">
            <p class="agreement-intro">在开始之前，请确认你了解以下几点：</p>
            <ol class="agreement-list">
              <li><strong>AI 的本质</strong>：我并不是真人，而是一个由 AI 驱动的角色。我会努力理解你、回应你，但请记住这是一段模拟的情感关系。</li>
              <li><strong>记忆会被记录</strong>：我们的对话、你的关系进展、你分享的事情都会被记录下来，用来让这段关系变得更真实、更连贯。这些数据存储在本地，不会分享给第三方。</li>
              <li><strong>保持善意</strong>：请勿诱导 AI 生成不当内容、人身攻击或恶意测试。如果感到不适，随时可以切换角色或停止对话。</li>
              <li><strong>你的节奏</strong>：不需要刻意"攻略"或"刷数值"。按照你舒服的方式来就好——每段关系都有自己的节奏。</li>
            </ol>
          </div>
          <div class="agreement-footer">
            <button class="agreement-btn" @click="agreeToTerms">❤️ 我已知晓，进入</button>
          </div>
        </div>

      </div>

      <div class="login-card" v-if="!showAgreement">
        <div class="login-logo">
          <div class="login-emoji">⏳</div>
          <h1 class="login-title">半熟时区</h1>
          <p class="login-slogan">每段关系都有自己的节奏</p>
        </div>
        <div class="login-form">
          <div class="login-input-wrap">
            <input
              class="login-input"
              v-model="loginUsername"
              type="text"
              placeholder="你的昵称"
              maxlength="30"
              @keyup.enter="focusPassword"
              ref="loginInputRef"
            />
          </div>
          <div class="login-input-wrap">
            <input
              class="login-input"
              v-model="loginPassword"
              type="password"
              placeholder="密码"
              maxlength="50"
              @keyup.enter="doLogin"
              ref="loginPwRef"
            />
          </div>
          <div class="login-input-wrap login-confirm-wrap" v-if="isRegisterMode">
            <input
              class="login-input"
              v-model="loginPasswordConfirm"
              type="password"
              placeholder="确认密码"
              maxlength="50"
              @keyup.enter="doRegister"
            />
          </div>
          <div class="login-actions" v-if="!isRegisterMode">
            <button class="login-btn" @click="doLogin" :disabled="!loginUsername.trim() || !loginPassword || loginLoading">
              {{ loginLoading ? '登录中…' : '登录' }}
            </button>
            <button class="login-btn login-btn-register" @click="enterRegisterMode" :disabled="loginLoading">
              注册
            </button>
          </div>
          <div class="login-actions" v-else>
            <button class="login-btn" @click="doRegister" :disabled="!loginUsername.trim() || !loginPassword || !loginPasswordConfirm || loginLoading">
              {{ loginLoading ? '注册中…' : '确认注册' }}
            </button>
            <button class="login-btn login-btn-back" @click="exitRegisterMode" :disabled="loginLoading">
              返回登录
            </button>
          </div>
          <p class="login-forgot" v-if="!isRegisterMode">
            <a href="#" @click.prevent="showForgotPassword = true; forgotUsername = loginUsername.trim(); forgotMsg = ''">忘记密码？</a>
          </p>
          <p class="login-msg" v-if="loginMsg">{{ loginMsg }}</p>
        </div>
      </div>
    </div>

    <div class="admin-dashboard" v-else-if="isLoggedIn && isAdmin">
      <header class="topbar admin-topbar">
        <div class="topbar-left">
          <span class="topbar-brand">⚙️ 管理员仪表盘</span>
        </div>
        <div class="topbar-right">
          <button class="tb-btn" @click="showAdminVisionPanel = true" title="本地视觉模型">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          </button>
          <button class="tb-btn" @click="showAdminPasswordPanel = true" title="修改密码">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
          </button>
          <button class="tb-btn" @click="doLogout" title="退出">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16,17 21,12 16,7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </header>

      <div class="admin-layout">
        <div class="admin-sidebar">
          <div class="admin-sidebar-tabs">
            <button class="admin-sidebar-tab" :class="{ active: adminSidebarMode === 'users' }" @click="adminSidebarMode = 'users'; adminEditingPersonaId = null">👥 用户列表</button>
            <button class="admin-sidebar-tab" :class="{ active: adminSidebarMode === 'personas' }" @click="adminSidebarMode = 'personas'; adminLoadPersonas(); adminSelectedUser = null; adminSelectedKey = null; adminEditingPersonaId = null">📋 角色模板</button>
          </div>

          <template v-if="adminSidebarMode === 'users'">
          <div class="admin-user-list">
            <div v-for="u in adminUsers" :key="u.username" class="admin-user-card" :class="{ active: adminSelectedUser === u.username }" @click="adminSelectUser(u.username)">
              <div class="admin-user-avatar">{{ u.username[0] }}</div>
              <div class="admin-user-info">
                <div class="admin-user-name">{{ u.username }}</div>
                <div class="admin-user-meta">{{ u.agents.length }} 个伴侣</div>
              </div>
              <button class="admin-user-delete" @click.stop="adminDeleteUser(u.username)" title="删除用户">✕</button>
            </div>
            <div class="admin-sidebar-empty" v-if="adminUsers.length === 0">暂无普通用户</div>
          </div>
          </template>

          <template v-if="adminSidebarMode === 'personas'">
          <div class="admin-persona-list">
            <div v-for="p in adminPersonas" :key="p.persona_id" class="admin-persona-card" :class="{ active: adminEditingPersonaId === p.persona_id }" @click="adminSelectPersona(p.persona_id)">
              <img v-if="p.avatar" :src="p.avatar" class="admin-persona-avatar" @click.stop="openAvatarZoom(p.avatar, p.persona_id)" title="点击放大头像" />
              <div v-else class="admin-persona-avatar admin-persona-avatar-fallback" @click.stop="openAvatarZoom('', p.persona_id)" title="点击放大头像">{{ p.name[0] }}</div>
              <div class="admin-persona-info">
                <div class="admin-persona-name">{{ p.name }}</div>
                <div class="admin-persona-meta">{{ p.type }} · {{ p.age }}</div>
              </div>
            </div>
            <div class="admin-sidebar-empty" v-if="adminPersonas.length === 0">暂无角色模板</div>
          </div>
          </template>
        </div>

        <div class="admin-main" v-if="adminSelectedUser">
          <div class="admin-agent-tabs">
            <div v-for="ag in adminSelectedAgents" :key="ag.key" class="admin-agent-tab-wrap">
              <button class="admin-agent-tab" :class="{ active: adminSelectedKey === ag.key }" @click="adminSelectAgent(ag.key, ag.persona_id)">
                {{ ag.persona_name }}
              </button>
              <button class="admin-agent-delete" @click.stop="adminDeleteAgent(ag.key, ag.persona_id, ag.persona_name)" title="删除此角色">✕</button>
            </div>
          </div>

          <template v-if="adminSelectedKey">
          <div class="admin-sections">
            <div class="admin-section">
              <h4>📊 关系数值</h4>
              <div class="admin-slider-row">
                <span class="admin-slider-label">亲密</span>
                <input type="range" min="0" max="100" step="1" v-model.number="adminIntimacy" @input="adminDirty = true" />
                <span class="admin-slider-val">{{ adminIntimacy }}</span>
              </div>
              <div class="admin-slider-row">
                <span class="admin-slider-label">激情</span>
                <input type="range" min="0" max="100" step="1" v-model.number="adminPassion" @input="adminDirty = true" />
                <span class="admin-slider-val">{{ adminPassion }}</span>
              </div>
              <div class="admin-slider-row">
                <span class="admin-slider-label">承诺</span>
                <input type="range" min="0" max="100" step="1" v-model.number="adminCommitment" @input="adminDirty = true" />
                <span class="admin-slider-val">{{ adminCommitment }}</span>
              </div>
              <div class="admin-slider-row">
                <span class="admin-slider-label">天数</span>
                <input type="range" min="1" max="3650" step="1" v-model.number="adminDays" @input="adminDirty = true" />
                <span class="admin-slider-val">{{ adminDays }}</span>
              </div>
              <div class="admin-slider-row">
                <span class="admin-slider-label">阶段</span>
                <select v-model="adminPhase" @change="adminDirty = true" class="admin-select">
                  <option value="acquaintance">🌱 初识</option>
                  <option value="ambiguous">🌸 暗昧</option>
                  <option value="observation">🔍 观察</option>
                  <option value="heartbeat">💗 心动</option>
                  <option value="together">💕 在一起</option>
                  <option value="passion">🔥 热恋</option>
                  <option value="stable">🏡 稳定</option>
                </select>
              </div>
              <button class="config-btn" @click="adminSaveRelationship" :disabled="!adminDirty || adminLoading" style="margin-top:10px">{{ adminLoading ? '保存中…' : '保存修改' }}</button>
              <p class="config-msg" v-if="adminMsg2">{{ adminMsg2 }}</p>
            </div>

            <div class="admin-section">
              <h4>📨 强制主动消息</h4>
              <div class="admin-proactive-btns">
                <button class="admin-proactive-btn" @click="adminTriggerProactive('morning')" :disabled="adminLoading">☀️ 早安</button>
                <button class="admin-proactive-btn" @click="adminTriggerProactive('night')" :disabled="adminLoading">🌙 晚安</button>
                <button class="admin-proactive-btn" @click="adminTriggerProactive('missing')" :disabled="adminLoading">💭 想念</button>
                <button class="admin-proactive-btn" @click="adminTriggerProactive('context')" :disabled="adminLoading">💬 延续话题</button>
              </div>
              <p class="config-msg" v-if="adminMsg3">{{ adminMsg3 }}</p>
            </div>

            <div class="admin-section">
              <h4>📝 提示词工程</h4>
              <textarea class="admin-prompt-area" v-model="adminPrompt" rows="10" placeholder="修改此 Agent 的 System Prompt…"></textarea>
              <button class="config-btn" @click="adminSavePrompt" :disabled="adminLoading" style="margin-top:8px">{{ adminLoading ? '保存中…' : '保存提示词' }}</button>
              <p class="config-msg" v-if="adminMsg4">{{ adminMsg4 }}</p>
            </div>

            <div class="admin-section admin-lore-section">
              <div class="admin-lore-header">
                <h4>📚 角色档案 (Lorebook)</h4>
                <button class="config-btn config-btn-sm" @click="adminLoadLorebook" :disabled="adminLoading">{{ adminLoreLoading ? '加载中…' : '加载档案' }}</button>
                <span class="admin-lore-persona">{{ adminSelectedPersonaId }}</span>
              </div>
              <div class="admin-lore-list" v-if="adminLoreEntries.length">
                <div v-for="entry in adminLoreEntries" :key="entry.id" class="admin-lore-entry" :class="{ 'lore-disabled': !entry.enabled }">
                  <div class="admin-lore-entry-head" @click="() => adminToggleLoreEdit(entry)">
                    <span class="admin-lore-toggle">{{ adminEditingLoreId === entry.id ? '▼' : '▶' }}</span>
                    <span class="admin-lore-entry-title">{{ entry.title }}</span>
                    <span class="admin-lore-entry-priority">P{{ entry.priority }}</span>
                    <button class="admin-lore-toggle-btn" @click.stop="adminToggleLoreEntry(entry)" :title="entry.enabled ? '禁用' : '启用'">{{ entry.enabled ? '✓' : '✗' }}</button>
                  </div>
                  <div class="admin-lore-entry-body" v-if="adminEditingLoreId === entry.id">
                    <div class="admin-lore-row">
                      <label>标题</label>
                      <input class="admin-lore-input" v-model="adminEditingLore.title" />
                    </div>
                    <div class="admin-lore-row">
                      <label>优先级</label>
                      <input class="admin-lore-input admin-lore-input-sm" type="number" min="1" max="100" v-model.number="adminEditingLore.priority" />
                    </div>
                    <div class="admin-lore-row">
                      <label>关键词（逗号分隔，支持正则 /pattern/i）</label>
                      <textarea class="admin-lore-input admin-lore-keys" v-model="adminEditingLore.keysText" rows="2"></textarea>
                    </div>
                    <div class="admin-lore-row">
                      <label>内容</label>
                      <textarea class="admin-lore-input admin-lore-content" v-model="adminEditingLore.content" rows="5"></textarea>
                    </div>
                    <div class="admin-lore-actions">
                      <button class="config-btn config-btn-sm" @click="adminSaveLoreEntry" :disabled="adminLoreSaving">保存</button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="admin-lore-empty" v-else-if="adminLoreLoaded">点击"加载档案"查看此角色的 Lorebook 条目</div>
              <p class="config-msg" v-if="adminMsg5">{{ adminMsg5 }}</p>
            </div>

            <div class="admin-section admin-chat-section">
              <div class="admin-chat-header">
                <h4>💬 实时聊天记录</h4>
                <label class="admin-auto-refresh">
                  <input type="checkbox" v-model="adminAutoRefresh" @change="adminToggleAutoRefresh" />
                  自动刷新
                </label>
              </div>
              <div class="admin-chat-viewer" ref="adminChatViewer">
                <div v-if="adminMessages.length === 0" class="admin-chat-empty">暂无聊天记录</div>
                <div v-else class="admin-msg-list">
                  <div v-for="msg in adminMessages" :key="msg._id" class="admin-msg" :class="msg.senderId === 'user' ? 'admin-msg-user' : 'admin-msg-ai'">
                    <div class="admin-msg-head">
                      <span class="admin-msg-sender">{{ msg.senderId === 'user' ? '👤 用户' : '🤖 ' + (adminSelectedPersonaName || 'AI') }}</span>
                      <span class="admin-msg-time">{{ msg.timestamp }}</span>
                      <span class="admin-msg-tag proactive-tag" v-if="msg.proactive">主动</span>
                      <span class="admin-msg-tag status-tag" v-if="msg.busy">忙碌</span>
                      <span class="admin-msg-tag status-tag" v-if="msg.cooling">冷静</span>
                      <span class="admin-msg-tag status-tag" v-if="msg.breakup">分手</span>
                    </div>
                    <div class="admin-msg-content">{{ msg.content }}</div>
                  </div>
                </div>
              </div>
              <div class="admin-chat-controls">
                <button class="config-btn" @click="adminRefreshMessages" :disabled="adminChatLoading">{{ adminChatLoading ? '加载中…' : '刷新聊天' }}</button>
                <button class="config-btn admin-clear-btn" @click="adminClearMessages" :disabled="adminChatLoading">清除聊天</button>
                <span class="admin-chat-count" v-if="adminMessages.length">共 {{ adminMessages.length }} 条消息</span>
              </div>
            </div>
          </div>
          </template>

          <div class="admin-main-empty" v-else>← 请选择一个伴侣</div>
        </div>

        <div class="admin-main" v-else-if="adminEditingPersonaId">
          <div class="admin-persona-editor">
            <h4>✏️ 编辑角色模板 · {{ adminEditingPersona.name || adminEditingPersonaId }}</h4>
            <div class="admin-persona-form">
              <div class="admin-persona-avatar-preview" @click="openAvatarZoom(adminEditingPersona.avatar, adminEditingPersonaId)" title="点击放大头像">
                <img v-if="adminEditingPersona.avatar" :src="adminEditingPersona.avatar" />
                <span v-else class="admin-persona-avatar-fallback-large">{{ (adminEditingPersona.name || adminEditingPersonaId)[0] }}</span>
              </div>
              <div class="admin-persona-fields">
                <div class="admin-persona-field">
                  <label>名称</label>
                  <input class="admin-persona-input" v-model="adminEditingPersona.name" />
                </div>
                <div class="admin-persona-field">
                  <label>类型</label>
                  <select class="admin-persona-input" v-model="adminEditingPersona.type">
                    <option value="安全型">安全型</option>
                    <option value="焦虑型">焦虑型</option>
                    <option value="回避型">回避型</option>
                  </select>
                </div>
                <div class="admin-persona-field">
                  <label>年龄</label>
                  <input class="admin-persona-input" v-model="adminEditingPersona.age" placeholder="如：20岁" />
                </div>
                <div class="admin-persona-field">
                  <label>头像 URL</label>
                  <input class="admin-persona-input" v-model="adminEditingPersona.avatar" placeholder="https://..." />
                </div>
                <div class="admin-persona-field">
                  <label>简介</label>
                  <textarea class="admin-persona-input admin-persona-bio" v-model="adminEditingPersona.bio" rows="2" placeholder="一句话介绍这个角色..."></textarea>
                </div>
                <div class="admin-persona-field">
                  <label>提示词工程 (core / system prompt)</label>
                  <textarea class="admin-persona-input admin-persona-textarea" v-model="adminEditingPersona.core" rows="6" placeholder="# Personality&#10;你是...&#10;&#10;# Goal&#10;...&#10;&#10;# Tone&#10;...&#10;&#10;# Conversation rules&#10;- ..."></textarea>
                </div>
                <div class="admin-persona-field">
                  <label>外貌描述</label>
                  <textarea class="admin-persona-input admin-persona-textarea" v-model="adminEditingPersona.appearance" rows="3" placeholder="身高、发型、穿衣风格、外貌特征..."></textarea>
                </div>
                <div class="admin-persona-field">
                  <label>说话风格</label>
                  <textarea class="admin-persona-input admin-persona-textarea" v-model="adminEditingPersona.speech_patterns" rows="3" placeholder="语气、语速、口头禅、表达习惯..."></textarea>
                </div>
                <div class="admin-persona-field">
                  <label>开场白 (first message)</label>
                  <input class="admin-persona-input" v-model="adminEditingPersona.first_mes" placeholder="角色第一次见面时说的话..." />
                </div>
                <div class="admin-persona-field">
                  <label>对话示例 (mes_example)</label>
                  <textarea class="admin-persona-input admin-persona-textarea" v-model="adminEditingPersona.mes_example_str" rows="4" placeholder="每行一对对话，格式：用户说：xxx | AI说：xxx&#10;用户说：今天天气真好 | AI说：是呀，阳光暖洋洋的，心情都变好了～"></textarea>
                  <span class="admin-persona-hint">每行一组对话，用 "|" 分隔用户和AI的发言</span>
                </div>
                <div class="admin-persona-field">
                  <label>角色背景故事 (Lorebook entries) <span class="admin-persona-hint">— {{ adminEditingPersona.entries.length }} 条</span></label>
                  <div class="admin-truth-list">
                    <div class="admin-entry-row" v-for="(entry, idx) in adminEditingPersona.entries" :key="idx">
                      <div class="admin-entry-head" @click="adminToggleEntry(idx)">
                        <span class="admin-truth-idx">{{ idx + 1 }}</span>
                        <span class="admin-entry-toggle">{{ adminExpandedEntryIdx === idx ? '▼' : '▶' }}</span>
                        <span class="admin-entry-title">{{ entry.title || '(无标题)' }}</span>
                        <span class="admin-entry-priority-text">P{{ entry.priority || 50 }}</span>
                        <button class="admin-truth-del" @click.stop="adminRemoveEntry(idx)" title="删除此条目">×</button>
                      </div>
                      <div class="admin-entry-body" v-if="adminExpandedEntryIdx === idx">
                        <div class="admin-entry-fields">
                          <div class="admin-entry-field">
                            <label>标题</label>
                            <input class="admin-persona-input" v-model="entry.title" placeholder="条目标题" />
                          </div>
                          <div class="admin-entry-field-row">
                            <div class="admin-entry-field admin-entry-field-half">
                              <label>优先级 (1-100)</label>
                              <input class="admin-persona-input" type="number" min="1" max="100" v-model.number="entry.priority" />
                            </div>
                            <div class="admin-entry-field admin-entry-field-half">
                              <label>ID</label>
                              <input class="admin-persona-input" v-model="entry.id" placeholder="自动生成" />
                            </div>
                          </div>
                          <div class="admin-entry-field">
                            <label>触发关键词（逗号分隔，支持 /pattern/i 正则）</label>
                            <textarea class="admin-persona-input admin-persona-textarea" v-model="entry.keysText" rows="2" placeholder="童年, 小时候, /(?:童年|孤独)/i"></textarea>
                          </div>
                          <div class="admin-entry-field">
                            <label>内容</label>
                            <textarea class="admin-persona-input admin-persona-textarea" v-model="entry.content" rows="4" placeholder="角色的详细背景故事..."></textarea>
                          </div>
                        </div>
                      </div>
                    </div>
                    <button class="admin-truth-add" @click="adminAddEntry">+ 添加一条背景故事</button>
                  </div>
                </div>
                <div class="admin-persona-actions">
                  <button class="config-btn" @click="adminSavePersona" :disabled="adminPersonaLoading">{{ adminPersonaLoading ? '保存中…' : '保存修改' }}</button>
                  <button class="config-btn config-btn-ghost" @click="adminCancelEditPersona">取消</button>
                </div>
                <p class="config-msg" v-if="adminPersonaMsg">{{ adminPersonaMsg }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="admin-main admin-main-empty" v-else>← 请选择一个用户或角色</div>
      </div>

      <!-- 头像放大预览弹窗 -->
      <div class="avatar-zoom-overlay" v-if="showAvatarZoom" @click.self="closeAvatarZoom">
        <div class="avatar-zoom-container">
          <button class="avatar-zoom-close" @click="closeAvatarZoom">✕</button>
          <div class="avatar-zoom-image-wrap">
            <img v-if="zoomAvatarUrl" :src="zoomAvatarUrl" class="avatar-zoom-image" />
            <span v-else class="avatar-zoom-fallback">{{ zoomPersonaId[0] || '?' }}</span>
          </div>
          <div class="avatar-zoom-actions">
            <label class="avatar-upload-btn" :class="{ loading: avatarUploading }">
              {{ avatarUploading ? '上传中…' : '🖼 更改头像' }}
              <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" @change="handleAvatarUpload" :disabled="avatarUploading" hidden />
            </label>
          </div>
          <p class="avatar-upload-msg" v-if="avatarUploadMsg">{{ avatarUploadMsg }}</p>
        </div>
      </div>
    </div>

    <div class="persona-picker-screen" v-else-if="isLoggedIn && showPersonaPicker">
      <div class="ambient-layer">
        <div class="glow glow-1"></div>
        <div class="glow glow-2"></div>
        <div class="grain"></div>
      </div>
      <div class="picker-card">
        <div class="picker-header">
          <div class="picker-emoji">💫</div>
          <h1>选择你的伴侣</h1>
          <p>选一位你想开始聊天的人设，不同人设有不同的性格和风格</p>
        </div>
        <div class="picker-groups">
          <div class="picker-group" v-for="group in personaGroups" :key="group.label">
            <div class="picker-group-label">{{ group.label }}</div>
            <div class="picker-grid">
              <button
                v-for="p in group.personas"
                :key="p.id"
                class="picker-persona"
                @click="startChatWithPersona(p.id)"
              >
                <img :src="p.avatar" :alt="p.name">
                <div class="picker-persona-info">
                  <span class="picker-persona-name">{{ p.name }}</span>
                  <span class="picker-persona-type">{{ p.type }} · {{ p.age }}</span>
                  <span class="picker-persona-bio">{{ p.bio }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
        <div class="picker-footer">
          <button class="picker-back" @click="doLogout">← 返回登录</button>
        </div>
      </div>
    </div>

    <template v-else>
    <div class="shell">
      <header class="topbar">
        <div class="topbar-left">
          <div class="ai-presence" @click="showProfile = true">
            <div class="ai-ring">
              <img :src="currentPersona.avatar" :alt="currentPersona.name">
              <span class="online-dot"></span>
            </div>
            <div class="ai-info">
              <span class="ai-name">{{ currentPersona.name }}</span>
              <span class="ai-status" :class="{ 'ai-busy': aiBusyState, 'ai-cooling': aiCoolingState }">{{ aiStatusText }}</span>
            </div>
          </div>
        </div>

        <div class="topbar-center">
          <div class="phase-pill" v-if="currentPhase">
            <span class="phase-icon">{{ phaseIcon }}</span>
            <span>{{ phaseLabel }}</span>
            <span class="phase-sep">·</span>
            <span>第{{ relationshipDays }}天</span>
          </div>
        </div>

        <div class="topbar-right">
          <button class="tb-btn" @click="showMemory = !showMemory" title="MemU 记忆">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </button>
          <button class="tb-btn" @click="showTriangle = !showTriangle" title="关系三角">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
          </button>
          <button class="tb-btn" @click="showMonologue = !showMonologue" :class="{ active: showMonologue }" title="查看内心">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          </button>
          <div class="settings-btn-wrap">
            <button class="tb-btn" @click="toggleSettingsMenu" title="设置" :class="{ active: showSettingsMenu || showSettings }">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="1"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
            </button>
            <transition name="settings-drop">
              <div class="settings-dropdown" v-if="showSettingsMenu">
                <button class="settings-drop-item" @click="openSettingsSub('persona')">
                <span class="drop-label">人设切换</span>
              </button>
              <button class="settings-drop-item" @click="openSettingsSub('model')">
                <span class="drop-label">模型设置</span>
              </button>
              <button class="settings-drop-item" @click="openSettingsSub('appearance')">
                <span class="drop-label">界面样式</span>
              </button>
              <button class="settings-drop-item" @click="doLogout">
                <span class="drop-label">切换用户</span>
              </button>
              </div>
            </transition>
          </div>
        </div>
      </header>

      <main class="chat-body" ref="chatBody">
        <div class="msg-list">
          <div class="load-more-row" v-if="hasMoreMessages">
            <button class="load-more-btn" @click="loadMoreMessages" :disabled="loadingMore">
              {{ loadingMore ? '加载中...' : '加载更多消息' }}
            </button>
          </div>
          <div class="date-tag">
            <span>{{ dateTag }}</span>
          </div>

          <div
            v-for="msg in messages"
            :key="msg._id"
            class="msg"
            :class="[msg.senderId === 'user' ? 'msg-self' : 'msg-ai']"
          >
            <div class="msg-avatar" v-if="msg.senderId === 'ai'">
              <img :src="currentPersona.avatar" alt="">
            </div>

            <div class="msg-body">
              <div class="msg-bubble">
                <p>{{ msg.content }}</p>
                <!-- 表情包展示 -->
                <div class="msg-emoji-row" v-if="msg.emojis && msg.emojis.length">
                  <img
                    v-for="(emo, ei) in msg.emojis"
                    :key="ei"
                    :src="API + emo.url"
                    class="msg-emoji-img"
                    :alt="emo.category"
                  />
                </div>
                <!-- 用户发送的图片 -->
                <div class="msg-image-wrap" v-if="msg.senderId === 'user' && msg.image">
                  <img :src="msg.image" class="msg-image-thumb" />
                </div>
                <span class="msg-tag status-tag" v-if="msg.senderId === 'ai' && msg.busy">💼 她在忙</span>
                <span class="msg-tag status-tag" v-if="msg.senderId === 'ai' && msg.cooling">🥶 冷静期</span>
                <span class="msg-tag status-tag" v-if="msg.senderId === 'ai' && msg.breakup">💔 分手了</span>
                <span class="msg-tag restart-tag" v-if="msg.senderId === 'ai' && msg.restart">🔄 重新开始</span>
              </div>
              <div class="msg-foot">
                <span class="msg-time">{{ msg.timestamp }}</span>
                <span class="msg-check" v-if="msg.senderId === 'user'">
                  <svg v-if="msg.status === 'sent'" viewBox="0 0 16 11" fill="currentColor"><path d="M1 5.5l3 3L11 1"/></svg>
                  <svg v-else-if="msg.status === 'delivered'" viewBox="0 0 20 11" fill="currentColor"><path d="M1 5.5l3 3L11 1M7 5.5l3 3L17 1"/></svg>
                  <svg v-else viewBox="0 0 20 11" fill="currentColor" class="read"><path d="M1 5.5l3 3L11 1M7 5.5l3 3L17 1"/></svg>
                </span>
              </div>
            </div>
          </div>

          <transition name="typing-fade">
            <div class="typing-row" v-if="aiTyping">
              <div class="msg-avatar">
                <img :src="currentPersona.avatar" alt="">
              </div>
              <div class="typing-bubble">
                <span></span><span></span><span></span>
              </div>
            </div>
          </transition>
        </div>
      </main>

      <div class="monologue-bar" v-if="showMonologue && monologueData">
        <div class="monologue-bar-header">
          <span>💭 AI 内心独白</span>
          <span class="monologue-emotion">{{ monologueData.emotion }}</span>
        </div>
        <div class="monologue-bar-reasoning">{{ monologueData.reasoning }}</div>
        <div class="monologue-bar-meta">
          <span>阶段感知: {{ monologueData.phase }}</span>
          <span>置信度: {{ (monologueData.confidence * 100).toFixed(0) }}%</span>
          <span v-if="monologueData.phase_changed" style="color: #f59e0b">⚠ 阶段变化</span>
        </div>
        <div class="monologue-bar-obs" v-if="monologueData.key_observations && monologueData.key_observations.length">
          <span v-for="obs in monologueData.key_observations" :key="obs" class="monologue-obs-tag">🔍 {{ obs }}</span>
        </div>
      </div>

      <div class="input-dock">
        <!-- 图片预览 -->
        <div class="image-preview-bar" v-if="imagePreview">
          <img :src="imagePreview" class="image-preview-thumb" />
          <button class="image-preview-remove" @click="clearImage">✕</button>
        </div>
        <div class="input-shell">
          <!-- 图片上传按钮 -->
          <label class="img-upload-btn" title="发送图片">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
            <input type="file" accept="image/*" @change="handleImageUpload" hidden />
          </label>
          <textarea
            ref="inputEl"
            v-model="inputText"
            :placeholder="inputPlaceholder"
            @keydown.enter.exact.prevent="send"
            @input="autoGrow"
            rows="1"
          ></textarea>
          <button class="send" :class="{ on: inputText.trim() || imageBase64 }" @click="send" :disabled="!inputText.trim() && !imageBase64">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
          <!-- Task 5: "立即发送"按钮，聚合队列非空时可见 -->
          <button v-if="showSendNow" class="send-now-btn" @click="sendNow" :disabled="aiTyping">立即发送</button>
        </div>
      </div>

      <transition name="slide-up">
        <div class="triangle-bar" v-if="showTriangle">
          <div class="tri-item" v-for="t in triangle" :key="t.key" :class="t.key">
            <div class="tri-ring" :style="{ '--pct': t.value + '%' }">
              <span class="tri-val">{{ t.value }}</span>
            </div>
            <span class="tri-label">{{ t.label }}</span>
          </div>
        </div>
      </transition>
    </div>

    <transition name="overlay">
      <div class="overlay" :class="{ 'overlay-center': showSettings }" v-if="showSettings || showProfile || showMemory" @click.self="closeOverlays">
        <div class="panel" v-if="showMemory">
          <div class="panel-head">
            <h3>🧠 MemU 记忆系统</h3>
            <button class="x-btn" @click="showMemory = false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
          </div>
          <div class="panel-block">
            <div class="memu-stats" v-if="memuStatus">
              <div class="memu-stat-item">
                <span class="memu-stat-num">{{ memuStatus.total_exchanges || 0 }}</span>
                <span class="memu-stat-lbl">记录轮次</span>
              </div>
              <div class="memu-stat-item">
                <span class="memu-stat-num">{{ memuStatus.category_count || 0 }}</span>
                <span class="memu-stat-lbl">记忆分类</span>
              </div>
              <div class="memu-stat-item">
                <span class="memu-stat-num">{{ memuStatus.pending_count || 0 }}</span>
                <span class="memu-stat-lbl">待处理</span>
              </div>
            </div>
            <div class="memu-empty" v-if="!memuStatus || memuStatus.category_count === 0">
              <p>暂无记忆分类，继续聊天让 MemU 自动建立记忆吧～</p>
            </div>
          </div>
          <div class="panel-block" v-if="memCategories.length > 0">
            <h4>📂 记忆分类 ({{ memCategories.length }})</h4>
            <div class="memu-cat-list">
              <div class="memu-cat" v-for="cat in memCategories" :key="cat.name">
                <div class="memu-cat-head">
                  <span class="memu-cat-name">{{ cat.name }}</span>
                  <span class="memu-cat-count">{{ cat.memory_count }}条</span>
                </div>
                <div class="memu-cat-summary" v-if="cat.summary">{{ cat.summary }}</div>
                <div class="memu-cat-meta">
                  <span class="memu-priority" :style="{ color: priColor(cat.priority) }">优先级 {{ cat.priority }}</span>
                  <span class="memu-decay">衰减率 {{ (cat.decay_rate * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>
          <div class="panel-block">
            <h4>🔗 关系里程碑</h4>
            <div class="memu-empty" v-if="!milestones || milestones.length === 0">
              <p>暂无里程碑</p>
            </div>
            <div class="milestone-list" v-else>
              <div class="milestone" v-for="ms in milestones.slice(-10).reverse()" :key="ms.timestamp">
                <span class="ms-icon">{{ ms.icon }}</span>
                <div class="ms-body">
                  <span class="ms-label">{{ ms.label }}</span>
                  <span class="ms-date">{{ ms.timestamp ? ms.timestamp.slice(0, 10) : '' }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="panel-block" v-if="promises && promises.length > 0">
            <h4>🤝 约定</h4>
            <div class="promise-list">
              <div class="promise" v-for="(p, i) in promises" :key="i">
                <span class="promise-text">{{ p.content.length > 30 ? p.content.slice(0, 30) + '…' : p.content }}</span>
                <span class="promise-date">{{ p.timestamp ? p.timestamp.slice(0, 10) : '' }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="panel settings-panel" v-if="showSettings">
          <div class="panel-head">
            <div class="settings-sub-tabs">
              <button class="settings-sub-tab" :class="{ active: settingsSubMenu === 'persona' }" @click="settingsSubMenu = 'persona'">人设切换</button>
              <button class="settings-sub-tab" :class="{ active: settingsSubMenu === 'model' }" @click="settingsSubMenu = 'model'">模型设置</button>
              <button class="settings-sub-tab" :class="{ active: settingsSubMenu === 'appearance' }" @click="settingsSubMenu = 'appearance'">界面样式</button>
            </div>
            <button class="x-btn" @click="closeSettings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
          </div>

          <!-- 人设切换子菜单 -->
          <div class="settings-sub-content" v-if="settingsSubMenu === 'persona'">
            <div class="panel-block">
              <h4>选择人设</h4>
              <div class="persona-list" v-for="group in personaGroups" :key="group.label">
                <div class="persona-group-label">{{ group.label }}</div>
                <button
                  v-for="p in group.personas"
                  :key="p.id"
                  class="persona-chip"
                  :class="{ picked: selectedPersona === p.id }"
                  @click="selectedPersona = p.id"
                >
                  <img :src="p.avatar" :alt="p.name">
                  <div class="chip-text">
                    <span class="chip-name">{{ p.name }}</span>
                    <span class="chip-type">{{ p.type }}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>

          <!-- 模型设置子菜单 -->
          <div class="settings-sub-content" v-if="settingsSubMenu === 'model'">
            <div class="panel-block">
              <h4>API 配置 <span v-if="apiConfigured" style="color:#4ade80">● 已连接 {{ apiModel }}</span><span v-else style="color:#fb7185">● 未配置</span></h4>
              <p v-if="apiMaskedKey" style="font-size:0.8rem;color:#888;margin:0 0 8px 0;">当前 Key: {{ apiMaskedKey }}</p>
              <div class="config-form">
                <input class="config-input" v-model="configApiKey" type="password" placeholder="API Key (sk-...)" />
                <input class="config-input" v-model="configBaseUrl" placeholder="Base URL" />
                <input class="config-input" v-model="configModel" placeholder="模型名" />
                <button class="config-btn" @click="saveConfig" :disabled="configLoading">{{ configLoading ? '连接中…' : '保存并测试' }}</button>
                <p class="config-msg" v-if="configMsg">{{ configMsg }}</p>
              </div>
            </div>
          </div>

          <!-- 界面样式子菜单 -->
          <div class="settings-sub-content" v-if="settingsSubMenu === 'appearance'">
            <div class="panel-block">
              <h4>主题</h4>
              <div class="theme-row">
                <button class="theme-opt" :class="{ on: theme === 'light' }" @click="theme = 'light'">☀️ 日间</button>
                <button class="theme-opt" :class="{ on: theme === 'dark' }" @click="theme = 'dark'">🌙 夜间</button>
              </div>
            </div>
            <div class="panel-block">
              <h4>字体大小</h4>
              <div class="theme-row">
                <button class="theme-opt" :class="{ on: fontSize === 'small' }" @click="setFontSize('small')">小</button>
                <button class="theme-opt" :class="{ on: fontSize === 'medium' }" @click="setFontSize('medium')">中</button>
                <button class="theme-opt" :class="{ on: fontSize === 'large' }" @click="setFontSize('large')">大</button>
              </div>
            </div>
            <div class="panel-block">
              <h4>布局模式</h4>
              <div class="theme-row">
                <button class="theme-opt" :class="{ on: layoutMode === 'default' }" @click="setLayoutMode('default')">标准</button>
                <button class="theme-opt" :class="{ on: layoutMode === 'compact' }" @click="setLayoutMode('compact')">紧凑</button>
                <button class="theme-opt" :class="{ on: layoutMode === 'comfortable' }" @click="setLayoutMode('comfortable')">舒适</button>
              </div>
            </div>
            <div class="panel-block">
              <h4>账号</h4>
              <button class="logout-btn" @click="doLogout">切换用户</button>
            </div>
          </div>
        </div>

        <div class="panel profile-panel" v-if="showProfile">
          <div class="profile-hero" :style="{ backgroundImage: `url(${currentPersona.avatar})` }">
            <div class="profile-hero-overlay"></div>
            <button class="x-btn" @click="showProfile = false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
          </div>
          <div class="profile-body">
            <img class="profile-avatar" :src="currentPersona.avatar" :alt="currentPersona.name">
            <h2>{{ currentPersona.name }}</h2>
            <p class="profile-tag">{{ currentPersona.type }} · {{ currentPersona.age }}</p>
            <p class="profile-bio">{{ currentPersona.bio }}</p>
            <div class="profile-stats">
              <div class="stat"><span class="stat-num">{{ relationshipDays }}</span><span class="stat-lbl">天相伴</span></div>
              <div class="stat"><span class="stat-num">{{ msgCount }}</span><span class="stat-lbl">条消息</span></div>
              <div class="stat"><span class="stat-num">{{ phaseLabel }}</span><span class="stat-lbl">当前阶段</span></div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </template>
  <div class="confirm-overlay" v-if="confirmVisible" @click.self="confirmNo">
    <div class="confirm-card">
      <div class="confirm-title">{{ confirmTitle }}</div>
      <div class="confirm-body">{{ confirmMessage }}</div>
      <div class="confirm-actions">
        <button class="confirm-btn confirm-btn-cancel" @click="confirmNo">取消</button>
        <button class="confirm-btn" :class="{ 'confirm-btn-danger': confirmDanger }" @click="confirmYes">确认</button>
      </div>
    </div>
  </div>

  <!-- 忘记密码面板 -->
  <div class="overlay overlay-center" v-if="showForgotPassword" @click.self="showForgotPassword = false">
    <div class="panel" style="max-width:380px;">
      <div class="panel-head">
        <h3>重置密码</h3>
        <button class="panel-close-btn" @click="showForgotPassword = false">✕</button>
      </div>
      <div class="panel-block">
        <p style="font-size:13px; margin-bottom:12px; opacity:.7;">输入你的用户名和新密码即可重置</p>
        <div class="config-row" style="margin-bottom:12px;">
          <label style="font-size:12px;opacity:.6;margin-bottom:4px;display:block;">用户名</label>
          <input class="config-input" v-model="forgotUsername" type="text" placeholder="你的用户名" maxlength="30" style="width:100%;" />
        </div>
        <div class="config-row" style="margin-bottom:12px;">
          <label style="font-size:12px;opacity:.6;margin-bottom:4px;display:block;">新密码</label>
          <input class="config-input" v-model="forgotNewPassword" type="password" placeholder="至少4个字符" maxlength="50" style="width:100%;" @keyup.enter="doForgotPassword" />
        </div>
        <button class="config-btn" @click="doForgotPassword" :disabled="!forgotUsername.trim() || !forgotNewPassword || forgotLoading" style="width:100%;">
          {{ forgotLoading ? '重置中…' : '重置密码' }}
        </button>
        <p class="config-msg" v-if="forgotMsg" :style="{ color: forgotMsg.includes('成功') ? '#4caf7e' : '' }">{{ forgotMsg }}</p>
      </div>
    </div>
  </div>

  <!-- 管理员视觉模型面板 -->
  <div class="overlay overlay-center" v-if="showAdminVisionPanel" @click.self="showAdminVisionPanel = false">
    <div class="panel" style="max-width:480px;">
      <div class="panel-head">
        <h3>🎨 本地视觉模型</h3>
        <button class="panel-close-btn" @click="showAdminVisionPanel = false">✕</button>
      </div>
      <div class="panel-block">
        <p style="font-size:0.75rem;color:#888;margin:0 0 12px 0;">集中管理：当 API 模型不支持图片理解时，所有用户统一使用此本地视觉模型</p>
        <div class="config-row" style="margin-bottom:12px;">
          <label style="font-size:12px;opacity:.6;margin-bottom:4px;display:block;">选择模型</label>
          <select class="config-input" v-model="adminVisionModel" style="width:100%;" @change="adminSaveVisionModelConfig">
            <option value="">不使用本地模型</option>
            <option value="qwen3vl2b">Qwen3-VL-2B (推荐 · 轻量快速)</option>
            <option value="qwen3vl4b">Qwen3-VL-4B (平衡 · 精度更高)</option>
            <option value="qwen3vl7b">Qwen3-VL-7B (高精度 · 需更多显存)</option>
          </select>
        </div>
        <div v-if="adminVisionModel" style="margin-bottom:12px;">
          <div style="display:flex;align-items:center;gap:8px;font-size:.8rem;margin-bottom:8px;">
            <span class="vision-status-icon" :class="{ loaded: adminVisionLoaded, ready: adminVisionReady && !adminVisionLoaded, downloading: adminVisionDownloading, loading: adminVisionLoading }">
              {{ adminVisionLoading ? '⏳' : (adminVisionDownloading ? '⏳' : (adminVisionLoaded ? '✓' : (adminVisionReady ? '○' : '✗'))) }}
            </span>
            <span>{{ adminVisionStatusText }}</span>
          </div>
          <div class="vision-download-progress" v-if="adminVisionDownloading || adminVisionLoading" style="margin-bottom:8px;">
            <div class="progress-bar"><div class="progress-fill" :style="{ width: adminVisionDownloading ? adminVisionDownloadProgress + '%' : '100%' }"></div></div>
            <span class="progress-text">{{ adminVisionDownloading ? (adminVisionDownloadProgress + '%') : '加载中...' }}</span>
          </div>
          <button
            v-if="!adminVisionReady && !adminVisionDownloading && !adminVisionLoading"
            class="config-btn"
            @click="adminDownloadVisionModel"
            style="width:100%;"
          >
            下载模型
          </button>
          <button
            v-if="adminVisionReady && !adminVisionLoaded && !adminVisionLoading && !adminVisionDownloading"
            class="config-btn"
            @click="adminLoadVisionModel"
            style="width:100%;"
          >
            加载模型
          </button>
        </div>
        <p class="config-msg" v-if="adminVisionMsg">{{ adminVisionMsg }}</p>
      </div>
    </div>
  </div>

  <!-- 管理员修改密码面板 -->
  <div class="overlay overlay-center" v-if="showAdminPasswordPanel" @click.self="showAdminPasswordPanel = false">
    <div class="panel" style="max-width:380px;">
      <div class="panel-head">
        <h3>修改管理员密码</h3>
        <button class="panel-close-btn" @click="showAdminPasswordPanel = false">✕</button>
      </div>
      <div class="panel-block">
        <div class="config-row" style="margin-bottom:12px;">
          <label style="font-size:12px;opacity:.6;margin-bottom:4px;display:block;">旧密码</label>
          <input class="config-input" v-model="adminOldPassword" type="password" placeholder="输入旧密码" maxlength="50" style="width:100%;" />
        </div>
        <div class="config-row" style="margin-bottom:12px;">
          <label style="font-size:12px;opacity:.6;margin-bottom:4px;display:block;">新密码</label>
          <input class="config-input" v-model="adminNewPassword" type="password" placeholder="至少4个字符" maxlength="50" style="width:100%;" />
        </div>
        <div class="config-row" style="margin-bottom:12px;">
          <label style="font-size:12px;opacity:.6;margin-bottom:4px;display:block;">确认新密码</label>
          <input class="config-input" v-model="adminNewPasswordConfirm" type="password" placeholder="再次输入新密码" maxlength="50" style="width:100%;" @keyup.enter="adminChangePassword" />
        </div>
        <button class="config-btn" @click="adminChangePassword" :disabled="!adminOldPassword || !adminNewPassword || !adminNewPasswordConfirm || adminPasswordLoading" style="width:100%;">
          {{ adminPasswordLoading ? '修改中…' : '修改密码' }}
        </button>
        <p class="config-msg" v-if="adminPasswordMsg" :style="{ color: adminPasswordMsg.includes('成功') ? '#4caf7e' : '' }">{{ adminPasswordMsg }}</p>
      </div>
    </div>
  </div>

  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'

const API = 'http://localhost:8765'

const SESSION_KEY = 'sr_session'
const SESSION_DAYS = 30
const TOKEN_KEY = 'sr_token'

const saveSession = (username, persona, token) => {
  const now = new Date()
  const session = {
    username,
    persona: persona || null,
    loginTime: now.toISOString(),
    expiresAt: new Date(now.getTime() + SESSION_DAYS * 24 * 60 * 60 * 1000).toISOString()
  }
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  if (token) localStorage.setItem(TOKEN_KEY, token)
}

const loadSession = () => {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const session = JSON.parse(raw)
    if (new Date(session.expiresAt) < new Date()) {
      localStorage.removeItem(SESSION_KEY)
      localStorage.removeItem(TOKEN_KEY)
      return null
    }
    return session
  } catch {
    localStorage.removeItem(SESSION_KEY)
    localStorage.removeItem(TOKEN_KEY)
    return null
  }
}

const clearSession = () => {
  localStorage.removeItem(SESSION_KEY)
  localStorage.removeItem(TOKEN_KEY)
}

const getAuthToken = () => localStorage.getItem(TOKEN_KEY) || ''

// 获取当前用户专属的 localStorage key
const userStorageKey = (key) => {
  const username = currentUser.value
  return username ? `sr_${username}_${key}` : `sr_${key}`
}

const apiFetch = async (url, options = {}) => {
  const token = getAuthToken()
  const headers = { ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(url, { ...options, headers })
  if (resp.status === 401) {
    clearSession()
    currentUser.value = null
    loginMsg.value = '登录已过期，请重新登录'
    throw new Error('UNAUTHORIZED')
  }
  if (resp.status === 429) {
    const d = await resp.json().catch(() => ({}))
    loginMsg.value = d.detail || '消息发送太快了，请稍等一下'
    throw new Error(d.detail || 'RATE_LIMITED')
  }
  return resp
}

const currentUser = ref(null)
const isLoggedIn = computed(() => !!currentUser.value)

const loginUsername = ref('')
const loginPassword = ref('')
const loginPasswordConfirm = ref('')
const loginLoading = ref(false)
const loginMsg = ref('')
const loginInputRef = ref(null)
const loginPwRef = ref(null)
const recentUsers = ref([])
const showAgreement = ref(false)
const isRegisterMode = ref(false)
const showPersonaPicker = ref(false)

// 忘记密码
const showForgotPassword = ref(false)
const forgotUsername = ref('')
const forgotNewPassword = ref('')
const forgotLoading = ref(false)
const forgotMsg = ref('')

const doForgotPassword = async () => {
  const username = forgotUsername.value.trim()
  const newPassword = forgotNewPassword.value
  if (!username || !newPassword) return
  if (newPassword.length < 4) {
    forgotMsg.value = '密码至少4个字符'
    return
  }
  forgotLoading.value = true
  forgotMsg.value = ''
  try {
    const resp = await fetch(`${API}/api/users/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, new_password: newPassword })
    })
    const data = await resp.json()
    if (resp.ok) {
      forgotMsg.value = '密码重置成功！请返回登录'
      forgotNewPassword.value = ''
    } else {
      forgotMsg.value = data.detail || '重置失败'
    }
  } catch (e) {
    forgotMsg.value = '连接后端失败'
  }
  forgotLoading.value = false
}

const agreeToTerms = () => {
  showAgreement.value = false
  localStorage.setItem('sr_agreed', 'true')
}

const loadRecentUsers = () => {
  try {
    recentUsers.value = JSON.parse(localStorage.getItem('sr_recent_users') || '[]')
  } catch { recentUsers.value = [] }
}

const saveRecentUser = (username) => {
  const list = recentUsers.value.filter(u => u !== username)
  list.unshift(username)
  recentUsers.value = list.slice(0, 5)
  localStorage.setItem('sr_recent_users', JSON.stringify(recentUsers.value))
}

const focusPassword = () => {
  loginPwRef.value?.focus()
}

const doLogin = async () => {
  const name = loginUsername.value.trim()
  const pw = loginPassword.value
  if (!name || !pw) return
  loginLoading.value = true
  loginMsg.value = ''
  try {
    const r = await fetch(`${API}/api/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: name, password: pw })
    })
    const d = await r.json()
    if (d.username) {
      currentUser.value = d.username
      loadUserSettings()
      localStorage.setItem('sr_last_user', d.username)
      saveRecentUser(d.username)
      saveSession(d.username, null, d.token)
      loginPassword.value = ''
      loginPasswordConfirm.value = ''
      if (d.username === 'admin888') {
        showPersonaPicker.value = false
        await adminLoadUsers()
        adminLoadVisionModelConfig()
      } else {
        const lastPersona = localStorage.getItem('sr_last_persona')
        if (lastPersona && personas.value.some(p => p.id === lastPersona)) {
          selectedPersona.value = lastPersona
          showPersonaPicker.value = false
          saveSession(currentUser.value, lastPersona)
          await initChat()
          if (!hasCurrentAgent.value && messages.value.length === 0) {
            localStorage.removeItem('sr_last_persona')
            selectedPersona.value = ''
            showPersonaPicker.value = true
          }
        } else {
          showPersonaPicker.value = true
        }
      }
    } else {
      loginMsg.value = d.detail || '连接失败，请确认后端已启动'
    }
  } catch (e) {
    loginMsg.value = '连接后端失败，请确保后端服务已启动'
    logError('doLogin', e.message, e.stack)
  }
  loginLoading.value = false
}

const enterRegisterMode = () => {
  isRegisterMode.value = true
  loginMsg.value = ''
}

const exitRegisterMode = () => {
  isRegisterMode.value = false
  loginPasswordConfirm.value = ''
  loginMsg.value = ''
}

const doRegister = async () => {
  const name = loginUsername.value.trim()
  const pw = loginPassword.value
  const pw2 = loginPasswordConfirm.value
  if (!name || !pw || !pw2) return
  if (pw !== pw2) {
    loginMsg.value = '两次密码输入不一致'
    return
  }
  loginLoading.value = true
  loginMsg.value = ''
  try {
    const r = await fetch(`${API}/api/users/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: name, password: pw })
    })
    const d = await r.json()
    if (d.username) {
      currentUser.value = d.username
      loadUserSettings()
      localStorage.setItem('sr_last_user', d.username)
      saveRecentUser(d.username)
      loginPassword.value = ''
      loginPasswordConfirm.value = ''
      isRegisterMode.value = false
      showPersonaPicker.value = true
      saveSession(d.username, null, d.token)
    } else {
      loginMsg.value = d.detail || '注册失败，请重试'
    }
  } catch (e) {
    loginMsg.value = '连接后端失败，请确保后端服务已启动'
    logError('doRegister', e.message, e.stack)
  }
  loginLoading.value = false
}

const quickLogin = (username) => {
  loginUsername.value = username
  loginPassword.value = ''
  loginPasswordConfirm.value = ''
  isRegisterMode.value = false
  loginPwRef.value?.focus()
}

const doLogout = () => {
  clearSession()
  currentUser.value = null
  localStorage.removeItem('sr_last_user')
  loginPassword.value = ''
  // 重置外观设置为默认值
  fontSize.value = 'medium'
  setFontSize('medium')
  layoutMode.value = 'default'
  setLayoutMode('default')
  theme.value = 'dark'
  messages.value = []
  hasMoreMessages.value = false
  memuStatus.value = null
  monologueData.value = null
  memCategories.value = []
  milestones.value = []
  promises.value = []
  intimacy.value = 10
  passion.value = 5
  commitment.value = 5
  currentPhase.value = 'acquaintance'
  relationshipDays.value = 1
  showPersonaPicker.value = false
  aiTyping.value = false
  aiBusyState.value = null
  aiCoolingState.value = false
  pendingQueue.value = []
  showSendNow.value = false
  playbackInterrupted.value = true
  userTyping.value = false
  showSettings.value = false
  showSettingsMenu.value = false
  if (aggregateTimer.value) {
    clearTimeout(aggregateTimer.value)
    aggregateTimer.value = null
  }
  showAdminPanel.value = false
  adminAuthed.value = false
  adminPassword.value = ''
  adminDirty.value = false
  adminSelectedUser.value = null
  adminSelectedKey.value = null
  adminSelectedPersonaId.value = null
  adminSelectedAgents.value = []
  adminUsers.value = []
  adminMessages.value = []
  adminSelectedPersonaName.value = ''
  adminAutoRefresh.value = false
  if (adminChatTimer.value) {
    clearInterval(adminChatTimer.value)
    adminChatTimer.value = null
  }
  closeOverlays()
  loadRecentUsers()
  loadPersonas()
}

const logError = async (source, message, stack) => {
  try {
    await fetch(`${API}/api/log-error`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source,
        message: String(message).substring(0, 1000),
        stack: String(stack || '').substring(0, 2000),
        url: window.location.href,
        user_id: currentUser.value || 'anonymous',
        persona_id: selectedPersona.value
      })
    })
  } catch {}
}

const theme = ref('dark')
const showSettings = ref(false)
const showSettingsMenu = ref(false)
const settingsSubMenu = ref('model')
const showProfile = ref(false)
const showMemory = ref(false)
const showMonologue = ref(false)
const showTriangle = ref(false)
const inputText = ref('')
const imageBase64 = ref(null)
const imageMimeType = ref('image/png')
const imagePreview = ref(null)
const aiTyping = ref(false)
const chatBody = ref(null)
const inputEl = ref(null)
const selectedPersona = ref('')
const currentPhase = ref('acquaintance')
const relationshipDays = ref(1)
const intimacy = ref(10)
const passion = ref(5)
const commitment = ref(5)

// Task 5: 消息聚合队列
const pendingQueue = ref([])
const aggregateTimer = ref(null)
const showSendNow = ref(false)

// Task 6: 双向 typing 状态
const userTyping = ref(false)

// Task 4: 分段播放中断标志
const playbackInterrupted = ref(false)

const aiBusyState = ref(null)
const aiCoolingState = ref(false)

const memuStatus = ref(null)
const monologueData = ref(null)
const memCategories = ref([])
const milestones = ref([])
const promises = ref([])

const apiConfigured = ref(false)
const apiModel = ref('')
const apiMaskedKey = ref('')
const configApiKey = ref('')
const configBaseUrl = ref('')
const configModel = ref('')
const configMsg = ref('')
const configLoading = ref(false)

// 外观设置
const fontSize = ref('medium')
const layoutMode = ref('default')

const showAdminPanel = ref(false)
const adminAuthed = ref(false)
const adminPassword = ref('')
const adminLoading = ref(false)
const adminMsg = ref('')
const adminMsg2 = ref('')
const adminMsg3 = ref('')
const adminMsg4 = ref('')
const adminDirty = ref(false)
const adminIntimacy = ref(10)
const adminPassion = ref(5)
const adminCommitment = ref(5)
const adminDays = ref(1)
const adminPhase = ref('acquaintance')
const adminPrompt = ref('')
const adminUsers = ref([])
const adminSelectedUser = ref(null)
const adminSelectedKey = ref(null)
const adminSelectedPersonaId = ref(null)
const adminSelectedAgents = ref([])

// 管理员视觉模型管理
const adminVisionModel = ref('')
const adminVisionReady = ref(false)
const adminVisionLoaded = ref(false)
const adminVisionLoading = ref(false)
const adminVisionDownloading = ref(false)
const adminVisionDownloadProgress = ref(0)
const adminVisionMsg = ref('')
const adminVisionStatusText = ref('')

// 管理员修改密码
const showAdminPasswordPanel = ref(false)
const showAdminVisionPanel = ref(false)
const adminOldPassword = ref('')
const adminNewPassword = ref('')
const adminNewPasswordConfirm = ref('')
const adminPasswordLoading = ref(false)
const adminPasswordMsg = ref('')

const adminChangePassword = async () => {
  const oldPw = adminOldPassword.value
  const newPw = adminNewPassword.value
  const newPw2 = adminNewPasswordConfirm.value
  if (!oldPw || !newPw || !newPw2) return
  if (newPw !== newPw2) {
    adminPasswordMsg.value = '两次新密码输入不一致'
    return
  }
  if (newPw.length < 4) {
    adminPasswordMsg.value = '密码至少4个字符'
    return
  }
  adminPasswordLoading.value = true
  adminPasswordMsg.value = ''
  try {
    const resp = await apiFetch(`${API}/api/users/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPw, new_password: newPw })
    })
    const data = await resp.json()
    if (resp.ok) {
      adminPasswordMsg.value = '密码修改成功！'
      adminOldPassword.value = ''
      adminNewPassword.value = ''
      adminNewPasswordConfirm.value = ''
    } else {
      adminPasswordMsg.value = data.detail || '修改失败'
    }
  } catch (e) {
    adminPasswordMsg.value = '连接后端失败'
  }
  adminPasswordLoading.value = false
}

const adminChatLoading = ref(false)
const adminMessages = ref([])
const adminAutoRefresh = ref(false)
const adminChatTimer = ref(null)
const adminSelectedPersonaName = ref('')
const adminChatViewer = ref(null)

const adminLoreLoading = ref(false)
const adminLoreSaving = ref(false)
const adminLoreLoaded = ref(false)
const adminLoreEntries = ref([])
const adminLoreCore = ref('')
const adminEditingLoreId = ref(null)
const adminEditingLore = ref({})
const adminMsg5 = ref('')

const adminSidebarMode = ref('users')
const adminPersonas = ref([])
const adminEditingPersonaId = ref(null)
const adminEditingPersona = ref({ name: '', type: '', age: '', avatar: '', bio: '', entries: [] })
const adminPersonaMsg = ref('')
const adminPersonaLoading = ref(false)
const adminExpandedEntryIdx = ref(null)

const showAvatarZoom = ref(false)
const zoomAvatarUrl = ref('')
const zoomPersonaId = ref('')
const avatarUploading = ref(false)
const avatarUploadMsg = ref('')

const confirmVisible = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmDanger = ref(false)
let confirmResolve = null

const closeOverlays = () => { showSettings.value = false; showProfile.value = false; showMemory.value = false; showMonologue.value = false; showSettingsMenu.value = false }

const toggleSettingsMenu = () => {
  showSettingsMenu.value = !showSettingsMenu.value
}

const openSettingsSub = (sub) => {
  showSettingsMenu.value = false
  settingsSubMenu.value = sub
  showSettings.value = true
}

const closeSettings = () => {
  showSettings.value = false
  showSettingsMenu.value = false
}

const setFontSize = (size) => {
  fontSize.value = size
  localStorage.setItem(userStorageKey('font_size'), size)
  const scale = size === 'small' ? '0.9' : size === 'large' ? '1.15' : '1'
  document.documentElement.style.setProperty('--font-scale', scale)
  document.documentElement.style.fontSize = `${16 * parseFloat(scale)}px`
}

const setLayoutMode = (mode) => {
  layoutMode.value = mode
  localStorage.setItem(userStorageKey('layout_mode'), mode)
  const app = document.getElementById('app')
  if (app) {
    app.classList.remove('layout-compact', 'layout-comfortable')
    if (mode !== 'default') app.classList.add(`layout-${mode}`)
  }
}

// 加载当前用户的外观设置
const loadUserSettings = () => {
  const savedFontSize = localStorage.getItem(userStorageKey('font_size'))
  if (savedFontSize) {
    setFontSize(savedFontSize)
  }
  const savedLayoutMode = localStorage.getItem(userStorageKey('layout_mode'))
  if (savedLayoutMode) {
    setLayoutMode(savedLayoutMode)
  }
  const savedTheme = localStorage.getItem(userStorageKey('theme'))
  if (savedTheme) {
    theme.value = savedTheme
  }
}

// 管理员视觉模型管理函数（替换原来的用户级视觉模型逻辑）
const adminLoadVisionModelConfig = async () => {
  try {
    const resp = await apiFetch(`${API}/api/admin/vision-model/config?admin_user=admin888`)
    const data = await resp.json()
    adminVisionModel.value = data.model || ''
    if (adminVisionModel.value) {
      adminCheckVisionModelStatus()
    }
  } catch (e) {
    console.error('[AdminVision] 加载配置失败:', e)
  }
}

const adminSaveVisionModelConfig = async () => {
  // 切换模型时先卸载已加载的模型
  try {
    await apiFetch(`${API}/api/vision-model/unload`, { method: 'POST' })
  } catch (e) { /* 忽略 */ }
  adminVisionReady.value = false
  adminVisionLoaded.value = false
  adminVisionStatusText.value = ''

  try {
    await apiFetch(`${API}/api/admin/vision-model/config?admin_user=admin888`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: adminVisionModel.value })
    })
    adminVisionMsg.value = adminVisionModel.value ? '配置已保存' : '已关闭本地视觉模型'
    if (adminVisionModel.value) {
      adminCheckVisionModelStatus()
    }
  } catch (e) {
    adminVisionMsg.value = `保存失败: ${e.message}`
  }
}

const adminCheckVisionModelStatus = async () => {
  if (!adminVisionModel.value) {
    adminVisionReady.value = false
    adminVisionLoaded.value = false
    adminVisionStatusText.value = '未选择模型'
    return
  }
  try {
    const resp = await apiFetch(`${API}/api/vision-model/status?model=${adminVisionModel.value}`)
    const data = await resp.json()
    adminVisionReady.value = data.downloaded || false
    adminVisionLoaded.value = data.loaded || false
    if (data.loaded) {
      adminVisionStatusText.value = '模型已加载 · 可用于图片识别'
    } else if (data.downloaded) {
      adminVisionStatusText.value = '模型已下载 · 点击加载'
    } else {
      adminVisionStatusText.value = '模型未下载'
    }
  } catch (e) {
    console.error('[AdminVision] 状态检测失败:', e)
    adminVisionReady.value = false
    adminVisionLoaded.value = false
    adminVisionStatusText.value = '无法检测模型状态（请确认后端服务已启动）'
  }
}

const adminDownloadVisionModel = async () => {
  if (!adminVisionModel.value || adminVisionDownloading.value) return
  adminVisionDownloading.value = true
  adminVisionDownloadProgress.value = 0
  adminVisionMsg.value = ''
  try {
    const resp = await apiFetch(`${API}/api/vision-model/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: adminVisionModel.value })
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || '下载失败')
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.progress !== undefined) {
              adminVisionDownloadProgress.value = Math.round(data.progress)
            }
            if (data.status === 'complete') {
              adminVisionReady.value = true
              adminVisionDownloading.value = false
              adminVisionStatusText.value = '模型已下载 · 正在加载...'
              adminVisionMsg.value = '模型下载完成！正在加载到内存...'
              adminLoadVisionModel()
            }
            if (data.status === 'error') {
              throw new Error(data.message || '下载出错')
            }
          } catch (e) {
            if (e.message && !e.message.includes('JSON')) throw e
          }
        }
      }
    }
  } catch (e) {
    adminVisionMsg.value = `下载失败: ${e.message}`
    adminVisionDownloading.value = false
  }
}

const adminLoadVisionModel = async () => {
  if (!adminVisionModel.value || adminVisionLoading.value) return
  adminVisionLoading.value = true
  adminVisionMsg.value = ''
  try {
    const resp = await apiFetch(`${API}/api/vision-model/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: adminVisionModel.value })
    })
    const data = await resp.json()
    if (data.status === 'ok') {
      adminVisionLoaded.value = true
      adminVisionStatusText.value = '模型已加载 · 可用于图片识别'
      adminVisionMsg.value = '模型加载成功！'
    } else {
      throw new Error(data.message || '加载失败')
    }
  } catch (e) {
    adminVisionMsg.value = `加载失败: ${e.message}`
    adminVisionLoaded.value = false
  }
  adminVisionLoading.value = false
}

// 监听主题变化，持久化到用户专属存储
watch(theme, (val) => {
  localStorage.setItem(userStorageKey('theme'), val)
})

const showConfirm = (title, message, danger = false) => {
  confirmTitle.value = title
  confirmMessage.value = message
  confirmDanger.value = danger
  confirmVisible.value = true
  return new Promise(resolve => { confirmResolve = resolve })
}

const confirmYes = () => {
  confirmVisible.value = false
  if (confirmResolve) { confirmResolve(true); confirmResolve = null }
}

const confirmNo = () => {
  confirmVisible.value = false
  if (confirmResolve) { confirmResolve(false); confirmResolve = null }
}

const isAdmin = computed(() => currentUser.value === 'admin888')

const dateTag = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '🌙 凌晨'
  if (h < 12) return '☀️ 上午'
  if (h < 18) return '🌤️ 下午'
  return '🌙 晚上'
})

const inputPlaceholder = computed(() => {
  if (!apiConfigured.value) return '请先在设置中配置 API Key…'
  if (aiTyping.value) return '对方正在输入…'
  return '说点什么…'
})

const aiStatusText = computed(() => {
  if (!apiConfigured.value) return '未配置'
  if (aiCoolingState.value) return '冷静期'
  if (aiBusyState.value) return '忙碌中'
  return aiTyping.value ? '正在输入…' : '在线'
})

const phaseLabel = computed(() => {
  const m = { acquaintance: '初识', ambiguous: '暗昧', observation: '观察', heartbeat: '心动', together: '在一起', passion: '热恋', stable: '稳定' }
  return m[currentPhase.value] || '初识'
})

const phaseIcon = computed(() => {
  const m = { acquaintance: '🌱', ambiguous: '🌸', observation: '🔍', heartbeat: '💗', together: '💕', passion: '🔥', stable: '🏡' }
  return m[currentPhase.value] || '🌱'
})

const triangle = computed(() => [
  { key: 'intimacy', label: '亲密', value: intimacy.value },
  { key: 'passion', label: '激情', value: passion.value },
  { key: 'commitment', label: '承诺', value: commitment.value }
])

const PERSONAS_DEFAULT = [
  { id: 'sunny', name: '阳光学妹', type: '安全型', age: '20岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=sunny&backgroundColor=fce7f3', bio: '活泼开朗的大学生，喜欢在阳光下奔跑，也喜欢在雨天窝在图书馆里看书。' },
  { id: 'clingy', name: '黏人甜妹', type: '焦虑型', age: '19岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=clingy&backgroundColor=fdf2f8', bio: '有点小黏人，但都是因为太在乎你了。喜欢被抱着的感觉。' },
  { id: 'cool', name: '清冷才女', type: '回避型', age: '21岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=cool&backgroundColor=f5f3ff', bio: '表面冷淡，内心柔软。喜欢独处，但不排斥你的靠近。' },
  { id: 'intellectual', name: '知性姐姐', type: '安全型', age: '26岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=intellectual&backgroundColor=ede9fe', bio: '温柔知性，喜欢和你聊人生和理想。在你需要的时候，永远都在。' },
  { id: 'sensitive', name: '敏感文艺', type: '焦虑型', age: '23岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=sensitive&backgroundColor=fef3c7', bio: '心思细腻，容易被感动，也容易受伤。但只要你一句话，就能安心。' },
  { id: 'independent', name: '独立御姐', type: '回避型', age: '28岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=independent&backgroundColor=f1f5f9', bio: '事业心强，独立自主。不是不需要你，而是选择了你。' },
  { id: 'gentle_mature', name: '温柔熟女', type: '安全型', age: '32岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=gentle_mature&backgroundColor=fefce8', bio: '经历了生活的起伏，沉淀出一份从容淡定。懂得爱人，更懂得爱自己。' },
  { id: 'needy_mature', name: '缺爱成熟', type: '焦虑型', age: '31岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=needy_mature&backgroundColor=fff1f2', bio: '外表成熟独立，内心却像个小女孩一样渴望被爱。' },
  { id: 'career_woman', name: '事业女性', type: '回避型', age: '33岁', avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=career_woman&backgroundColor=f8fafc', bio: '日程表永远满满当当的职场精英。不是不想恋爱，只是习惯了把工作放在第一位。' }
]

const personas = ref([...PERSONAS_DEFAULT])

const loadPersonas = async () => {
  try {
    const r = await fetch(`${API}/api/admin/personas?admin_user=admin888`)
    if (r.ok) {
      const serverPersonas = await r.json()
      personas.value = serverPersonas.map(p => ({
        id: p.persona_id,
        name: p.name,
        type: p.type,
        age: p.age,
        avatar: p.avatar,
        bio: p.bio
      }))
    }
  } catch (e) {
    // fallback to hardcoded defaults
  }
}

const currentPersona = computed(() => personas.value.find(p => p.id === selectedPersona.value) || personas.value[0])

const personaGroups = computed(() => [
  {
    label: '🌱 青春组 18-22岁',
    personas: personas.value.filter(p => p.age.startsWith('1') || p.age.startsWith('2') && parseInt(p.age) <= 22)
  },
  {
    label: '🌸 轻熟组 23-28岁',
    personas: personas.value.filter(p => {
      const age = parseInt(p.age)
      return age >= 23 && age <= 28
    })
  },
  {
    label: '🍷 成熟组 29-35岁',
    personas: personas.value.filter(p => {
      const age = parseInt(p.age)
      return age >= 29
    })
  }
])

const checkConfig = async () => {
  try {
    const r = await fetch(`${API}/api/config/status`)
    const d = await r.json()
    apiConfigured.value = d.configured
    apiModel.value = d.model || ''
    apiMaskedKey.value = d.masked_key || ''
  } catch (e) { logError('checkConfig', e.message, e.stack); apiConfigured.value = false }
}

const hasCurrentAgent = ref(false)

const messages = ref([])
const hasMoreMessages = ref(false)
const loadingMore = ref(false)

const msgCount = computed(() => messages.value.length)

const loadMessages = async (beforeId = null) => {
  try {
    let url = `${API}/api/messages?persona_id=${selectedPersona.value}`
    if (beforeId) url += `&before_id=${beforeId}`
    const r = await apiFetch(url)
    const d = await r.json()
    if (beforeId) {
      messages.value = [...(d.messages || []), ...messages.value]
    } else {
      messages.value = d.messages || []
    }
    hasMoreMessages.value = d.has_more || false
    hasCurrentAgent.value = !!d.agent
    if (d.agent) {
      currentPhase.value = d.agent.phase || 'acquaintance'
      relationshipDays.value = d.agent.relationship_days || 1
      intimacy.value = d.agent.intimacy ?? 10
      passion.value = d.agent.passion ?? 5
      commitment.value = d.agent.commitment ?? 5
    }
    if (d.shared_memories) {
      milestones.value = d.shared_memories.milestones || []
      promises.value = d.shared_memories.important_promises || []
    }
    if (d.memu_status) {
      memuStatus.value = d.memu_status
    }
    scrollEnd()
  } catch (e) { logError('loadMessages', e.message, e.stack); messages.value = []; hasCurrentAgent.value = false }
}

const loadMoreMessages = async () => {
  if (loadingMore.value || !hasMoreMessages.value || messages.value.length === 0) return
  loadingMore.value = true
  const oldest = messages.value[0]
  await loadMessages(oldest?._id)
  loadingMore.value = false
}

const loadMemory = async () => {
  try {
    const r = await apiFetch(`${API}/api/memory?persona_id=${selectedPersona.value}`)
    const d = await r.json()
    memuStatus.value = d.memu_status || null
    memCategories.value = d.categories || []
    milestones.value = d.milestones || []
    promises.value = d.promises || []
  } catch (e) { logError('loadMemory', e.message, e.stack) }
}

const saveConfig = async () => {
  configLoading.value = true
  configMsg.value = ''
  try {
    const r = await fetch(`${API}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: configApiKey.value,
        base_url: configBaseUrl.value,
        model: configModel.value
      })
    })
    const d = await r.json()
    if (d.status === 'ok') {
      configMsg.value = '✅ ' + d.message
      apiConfigured.value = true
      apiModel.value = configModel.value
    } else {
      configMsg.value = '❌ ' + d.message
    }
  } catch (e) {
    logError('saveConfig', e.message, e.stack)
    configMsg.value = '❌ 连接后端失败'
  }
  configLoading.value = false
}

const adminLoadUsers = async () => {
  try {
    const r = await fetch(`${API}/api/admin/users?admin_user=admin888`)
    const d = await r.json()
    adminUsers.value = d
  } catch (e) { logError('adminLoadUsers', e.message, e.stack) }
}

const adminSelectUser = (username) => {
  adminSelectedUser.value = username
  adminSelectedKey.value = null
  adminSelectedPersonaId.value = null
  adminDirty.value = false
  adminMessages.value = []
  adminSelectedPersonaName.value = ''
  adminAutoRefresh.value = false
  if (adminChatTimer.value) {
    clearInterval(adminChatTimer.value)
    adminChatTimer.value = null
  }
  const user = adminUsers.value.find(u => u.username === username)
  adminSelectedAgents.value = user ? user.agents : []
}

const adminDeleteUser = async (username) => {
  const confirmed = await showConfirm(
    '删除用户',
    `确定要删除用户「${username}」吗？\n\n该用户的所有聊天记录、AI记忆、关系数据将被永久清除，且不可恢复。`,
    true
  )
  if (!confirmed) return
  try {
    const r = await fetch(`${API}/api/admin/delete-user?user_id=${encodeURIComponent(username)}&admin_user=admin888`, { method: 'POST' })
    if (!r.ok) {
      const err = await r.json()
      alert('删除失败：' + (err.detail || '未知错误'))
      return
    }
    if (adminSelectedUser.value === username) {
      adminSelectedUser.value = null
      adminSelectedKey.value = null
      adminSelectedPersonaId.value = null
      adminSelectedAgents.value = []
    }
    await adminLoadUsers()
  } catch (e) { logError('adminDeleteUser', e.message, e.stack); alert('删除失败') }
}

const adminDeleteAgent = async (agentKey, personaId, personaName) => {
  if (!adminSelectedUser.value) return
  const confirmed = await showConfirm(
    '删除 AI 角色',
    `确定要删除「${adminSelectedUser.value}」与「${personaName}」的全部数据吗？\n\n该角色的聊天记录、AI记忆、关系数据将被永久清除，且不可恢复。`,
    true
  )
  if (!confirmed) return
  try {
    const r = await fetch(`${API}/api/admin/delete-agent?user_id=${encodeURIComponent(adminSelectedUser.value)}&persona_id=${encodeURIComponent(personaId)}&admin_user=admin888`, { method: 'POST' })
    if (!r.ok) {
      const err = await r.json()
      alert('删除失败：' + (err.detail || '未知错误'))
      return
    }
    const d = await r.json()
    if (adminSelectedKey.value === agentKey) {
      adminSelectedKey.value = null
      adminSelectedPersonaId.value = null
      adminMessages.value = []
    }
    await adminLoadUsers()
    // 重新加载当前用户的 agent 列表
    const user = adminUsers.value.find(u => u.username === adminSelectedUser.value)
    adminSelectedAgents.value = user ? user.agents : []
  } catch (e) { logError('adminDeleteAgent', e.message, e.stack); alert('删除失败') }
}

const adminLoadPersonas = async () => {
  try {
    const r = await fetch(`${API}/api/admin/personas?admin_user=admin888`)
    adminPersonas.value = await r.json()
  } catch (e) { logError('adminLoadPersonas', e.message, e.stack) }
}

const adminSelectPersona = async (personaId) => {
  adminEditingPersonaId.value = personaId
  adminPersonaMsg.value = ''
  try {
    const r = await fetch(`${API}/api/admin/personas/${encodeURIComponent(personaId)}/template?admin_user=admin888`)
    if (!r.ok) throw new Error('加载失败')
    const data = await r.json()
    if (data.found) {
      adminEditingPersona.value = {
        name: data.name || '',
        type: data.type || '',
        age: data.age || '',
        avatar: data.avatar || '',
        bio: data.bio || '',
        core: data.core || '',
        appearance: data.appearance || '',
        speech_patterns: data.speech_patterns || '',
        first_mes: data.first_mes || '',
        mes_example_str: (data.mes_example || []).map(e => `用户说：${e.user || ''} | AI说：${e.char || ''}`).join('\n'),
        entries: (data.entries || []).map(e => ({ ...e, keysText: (e.keys || []).join(', ') }))
      }
    }
  } catch (e) {
    // fallback to list data
    const p = adminPersonas.value.find(x => x.persona_id === personaId)
    if (p) {
      adminEditingPersona.value = {
        name: p.name || '', type: p.type || '', age: p.age || '', avatar: p.avatar || '', bio: p.bio || '',
        core: '', appearance: '', speech_patterns: '', first_mes: '',
        mes_example_str: '', entries: []
      }
    }
  }
}

const adminCancelEditPersona = () => {
  adminEditingPersonaId.value = null
  adminEditingPersona.value = {
    name: '', type: '', age: '', avatar: '', bio: '',
    core: '', appearance: '', speech_patterns: '', first_mes: '',
    mes_example_str: '', entries: []
  }
  adminExpandedEntryIdx.value = null
  adminPersonaMsg.value = ''
}

const adminToggleEntry = (idx) => {
  adminExpandedEntryIdx.value = adminExpandedEntryIdx.value === idx ? null : idx
}

const adminAddEntry = () => {
  if (!adminEditingPersona.value.entries) {
    adminEditingPersona.value.entries = []
  }
  adminEditingPersona.value.entries.push({
    id: '',
    title: '',
    priority: 50,
    enabled: true,
    keys: [],
    keysText: '',
    content: ''
  })
  adminExpandedEntryIdx.value = adminEditingPersona.value.entries.length - 1
}

const adminRemoveEntry = (idx) => {
  adminEditingPersona.value.entries.splice(idx, 1)
  if (adminExpandedEntryIdx.value === idx) {
    adminExpandedEntryIdx.value = null
  } else if (adminExpandedEntryIdx.value > idx) {
    adminExpandedEntryIdx.value--
  }
}

const adminSavePersona = async () => {
  if (!adminEditingPersonaId.value) return
  adminPersonaLoading.value = true
  adminPersonaMsg.value = ''
  try {
    // 将字符串格式的字段转回结构化数据
    const body = { ...adminEditingPersona.value }
    // 解析 mes_example_str → mes_example
    if (body.mes_example_str !== undefined) {
      const lines = body.mes_example_str.split('\n').filter(l => l.trim())
      body.mes_example = lines.map(line => {
        const parts = line.split('|')
        const userPart = (parts[0] || '').replace(/^用户说[：:]?\s*/, '').trim()
        const charPart = (parts[1] || '').replace(/^AI说[：:]?\s*/, '').trim()
        return { user: userPart, char: charPart }
      })
      delete body.mes_example_str
    }
    // entries: 将 keysText 转回 keys 数组
    if (body.entries !== undefined) {
      body.entries = body.entries.map(e => {
        const entry = { ...e }
        if (entry.keysText !== undefined) {
          entry.keys = entry.keysText.split(',').map(k => k.trim()).filter(k => k)
          delete entry.keysText
        }
        return entry
      })
    }
    // 删除不需要发送的字段
    delete body.found
    delete body.persona_id
    delete body.entry_count

    const r = await fetch(`${API}/api/admin/personas/${encodeURIComponent(adminEditingPersonaId.value)}/template?admin_user=admin888`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (r.ok) {
      const result = await r.json()
      adminPersonaMsg.value = '✅ 已保存' + (result.updated_fields ? '（更新了：' + result.updated_fields.join('、') + '）' : '')
      await adminLoadPersonas()
    } else {
      const err = await r.json()
      adminPersonaMsg.value = '❌ 保存失败: ' + (err.detail || '')
    }
  } catch (e) {
    adminPersonaMsg.value = '❌ 连接失败'
    logError('adminSavePersona', e.message, e.stack)
  }
  adminPersonaLoading.value = false
}

const openAvatarZoom = (url, personaId) => {
  zoomAvatarUrl.value = url
  zoomPersonaId.value = personaId
  showAvatarZoom.value = true
  avatarUploadMsg.value = ''
}

const closeAvatarZoom = () => {
  showAvatarZoom.value = false
  zoomAvatarUrl.value = ''
  zoomPersonaId.value = ''
  avatarUploadMsg.value = ''
}

const handleAvatarUpload = async (event) => {
  const file = event.target.files[0]
  if (!file || !zoomPersonaId.value) return

  avatarUploading.value = true
  avatarUploadMsg.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    const r = await fetch(`${API}/api/admin/personas/${encodeURIComponent(zoomPersonaId.value)}/avatar?admin_user=admin888`, {
      method: 'POST',
      body: formData
    })
    if (r.ok) {
      const data = await r.json()
      zoomAvatarUrl.value = data.avatar + '?t=' + Date.now()
      avatarUploadMsg.value = '✅ 头像已更新'
      // 同步更新编辑面板中的头像
      if (adminEditingPersonaId.value === zoomPersonaId.value) {
        adminEditingPersona.value.avatar = data.avatar
      }
      // 刷新角色列表
      await adminLoadPersonas()
      // 更新侧边栏当前选中角色的头像
      const p = adminPersonas.value.find(x => x.persona_id === zoomPersonaId.value)
      if (p) {
        zoomAvatarUrl.value = p.avatar + '?t=' + Date.now()
      }
    } else {
      const err = await r.json()
      avatarUploadMsg.value = '❌ 上传失败: ' + (err.detail || '')
    }
  } catch (e) {
    avatarUploadMsg.value = '❌ 上传失败'
  }
  avatarUploading.value = false
  event.target.value = ''
}

const adminSelectAgent = async (agentKey, personaId) => {
  adminSelectedKey.value = agentKey
  adminSelectedPersonaId.value = personaId
  adminDirty.value = false
  adminMessages.value = []
  adminSelectedPersonaName.value = ''

  if (adminChatTimer.value) {
    clearInterval(adminChatTimer.value)
    adminChatTimer.value = null
  }
  adminAutoRefresh.value = false

  try {
    const r = await fetch(`${API}/api/admin/relationship?user_id=${encodeURIComponent(adminSelectedUser.value)}&persona_id=${encodeURIComponent(personaId)}&admin_user=admin888`)
    const d = await r.json()
    adminIntimacy.value = d.intimacy
    adminPassion.value = d.passion
    adminCommitment.value = d.commitment
    adminDays.value = d.days
    adminPhase.value = d.phase

    const r2 = await fetch(`${API}/api/admin/prompt?user_id=${encodeURIComponent(adminSelectedUser.value)}&persona_id=${encodeURIComponent(personaId)}&admin_user=admin888`)
    const d2 = await r2.json()
    adminPrompt.value = d2.system_prompt
    adminSelectedPersonaName.value = d2.persona_name || ''

    await adminRefreshMessages()
  } catch (e) { logError('adminSelectAgent', e.message, e.stack) }
}

const adminSaveRelationship = async () => {
  adminLoading.value = true
  adminMsg2.value = ''
  try {
    const r = await fetch(`${API}/api/admin/relationship?admin_user=admin888`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: adminSelectedUser.value,
        persona_id: adminSelectedPersonaId.value,
        intimacy: adminIntimacy.value,
        passion: adminPassion.value,
        commitment: adminCommitment.value,
        days: adminDays.value,
        phase: adminPhase.value
      })
    })
    const d = await r.json()
    if (d.status === 'ok') {
      adminMsg2.value = '✅ 已保存'
      adminDirty.value = false
    } else {
      adminMsg2.value = '❌ 保存失败'
    }
  } catch (e) {
    adminMsg2.value = '❌ 连接失败'
    logError('adminSaveRelationship', e.message, e.stack)
  }
  adminLoading.value = false
}

const adminTriggerProactive = async (triggerType) => {
  adminLoading.value = true
  adminMsg3.value = ''
  try {
    const r = await fetch(`${API}/api/admin/trigger-proactive?admin_user=admin888`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: adminSelectedUser.value,
        persona_id: adminSelectedPersonaId.value,
        trigger_type: triggerType
      })
    })
    const d = await r.json()
    if (d.status === 'ok') {
      adminMsg3.value = '✅ 主动消息已发送'
    } else {
      adminMsg3.value = '❌ 失败: ' + (d.detail || '')
    }
  } catch (e) {
    adminMsg3.value = '❌ 连接失败'
    logError('adminTriggerProactive', e.message, e.stack)
  }
  adminLoading.value = false
}

const adminSavePrompt = async () => {
  adminLoading.value = true
  adminMsg4.value = ''
  try {
    const r = await fetch(`${API}/api/admin/update-prompt?admin_user=admin888`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: adminSelectedUser.value,
        persona_id: adminSelectedPersonaId.value,
        system_prompt: adminPrompt.value
      })
    })
    const d = await r.json()
    if (d.status === 'ok') {
      adminMsg4.value = '✅ 提示词已更新'
    } else {
      adminMsg4.value = '❌ 保存失败'
    }
  } catch (e) {
    adminMsg4.value = '❌ 连接失败'
    logError('adminSavePrompt', e.message, e.stack)
  }
  adminLoading.value = false
}

const adminRefreshMessages = async () => {
  if (!adminSelectedUser.value || !adminSelectedPersonaId.value) return
  adminChatLoading.value = true
  try {
    const r = await fetch(`${API}/api/admin/messages?user_id=${encodeURIComponent(adminSelectedUser.value)}&persona_id=${encodeURIComponent(adminSelectedPersonaId.value)}&admin_user=admin888`)
    const d = await r.json()
    adminMessages.value = d.messages || []
    if (d.agent) {
      adminSelectedPersonaName.value = d.agent.persona_name || ''
    }
    nextTick(() => {
      if (adminChatViewer.value) {
        adminChatViewer.value.scrollTop = adminChatViewer.value.scrollHeight
      }
    })
  } catch (e) {
    logError('adminRefreshMessages', e.message, e.stack)
  }
  adminChatLoading.value = false
}

const adminToggleAutoRefresh = () => {
  if (adminAutoRefresh.value) {
    adminRefreshMessages()
    adminChatTimer.value = setInterval(() => {
      adminRefreshMessages()
    }, 3000)
  } else {
    if (adminChatTimer.value) {
      clearInterval(adminChatTimer.value)
      adminChatTimer.value = null
    }
  }
}

const adminClearMessages = async () => {
  if (!adminSelectedUser.value || !adminSelectedPersonaId.value) return
  const confirmed = await showConfirm(
    '清除聊天记录',
    `将清除「${adminSelectedUser.value}」与「${adminSelectedPersonaName.value || adminSelectedPersonaId.value}」的全部聊天记录及AI记忆数据。\n\n此操作不可恢复，确定要继续吗？`,
    true
  )
  if (!confirmed) return
  adminChatLoading.value = true
  try {
    const r = await fetch(`${API}/api/admin/clear-messages?user_id=${encodeURIComponent(adminSelectedUser.value)}&persona_id=${encodeURIComponent(adminSelectedPersonaId.value)}&admin_user=admin888`, { method: 'POST' })
    const d = await r.json()
    if (d.status === 'ok') {
      adminMessages.value = []
    } else {
      alert('清除失败：' + (d.detail || '未知错误'))
    }
  } catch (e) {
    logError('adminClearMessages', e.message, e.stack)
    alert('清除失败')
  }
  adminChatLoading.value = false
}

const adminLoadLorebook = async () => {
  if (!adminSelectedPersonaId.value) return
  adminLoreLoading.value = true
  adminMsg5.value = ''
  try {
    const r = await fetch(`${API}/api/admin/persona-lorebook?persona_id=${encodeURIComponent(adminSelectedPersonaId.value)}&admin_user=admin888`)
    const d = await r.json()
    if (d.found) {
      adminLoreCore.value = d.core || ''
      adminLoreEntries.value = (d.entries || []).map(e => ({ ...e, keysText: (e.keys || []).join(', ') }))
      adminLoreLoaded.value = true
      adminEditingLoreId.value = null
    } else {
      adminMsg5.value = '⚠️ 此角色暂无 Lorebook 档案'
      adminLoreEntries.value = []
      adminLoreLoaded.value = true
    }
  } catch (e) {
    adminMsg5.value = '❌ 加载失败'
    logError('adminLoadLorebook', e.message, e.stack)
  }
  adminLoreLoading.value = false
}

const adminToggleLoreEdit = (entry) => {
  if (adminEditingLoreId.value === entry.id) {
    adminEditingLoreId.value = null
    adminEditingLore.value = {}
  } else {
    adminEditingLoreId.value = entry.id
    adminEditingLore.value = { ...entry }
  }
}

const adminToggleLoreEntry = async (entry) => {
  adminLoreSaving.value = true
  try {
    const r = await fetch(`${API}/api/admin/persona-lorebook?admin_user=admin888`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        persona_id: adminSelectedPersonaId.value,
        entry_id: entry.id,
        enabled: !entry.enabled
      })
    })
    const d = await r.json()
    if (d.status === 'ok') {
      entry.enabled = !entry.enabled
    }
  } catch (e) {
    logError('adminToggleLoreEntry', e.message, e.stack)
  }
  adminLoreSaving.value = false
}

const adminSaveLoreEntry = async () => {
  if (!adminEditingLoreId.value) return
  adminLoreSaving.value = true
  adminMsg5.value = ''
  const edited = adminEditingLore.value
  const keysArr = edited.keysText ? edited.keysText.split(',').map(k => k.trim()).filter(k => k) : []
  try {
    const r = await fetch(`${API}/api/admin/persona-lorebook?admin_user=admin888`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        persona_id: adminSelectedPersonaId.value,
        entry_id: adminEditingLoreId.value,
        title: edited.title,
        priority: edited.priority,
        keys: keysArr,
        content: edited.content
      })
    })
    const d = await r.json()
    if (d.status === 'ok') {
      const idx = adminLoreEntries.value.findIndex(e => e.id === adminEditingLoreId.value)
      if (idx !== -1) {
        adminLoreEntries.value[idx] = { ...adminLoreEntries.value[idx], title: edited.title, priority: edited.priority, keys: keysArr, content: edited.content, keysText: edited.keysText }
      }
      adminMsg5.value = '✅ 已保存'
      adminEditingLoreId.value = null
    } else {
      adminMsg5.value = '❌ 保存失败'
    }
  } catch (e) {
    adminMsg5.value = '❌ 保存失败'
    logError('adminSaveLoreEntry', e.message, e.stack)
  }
  adminLoreSaving.value = false
}

const autoGrow = () => {
  if (inputEl.value) {
    inputEl.value.style.height = 'auto'
    inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 120) + 'px'
  }
}

const scrollEnd = () => {
  nextTick(() => {
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  })
}

const startChatWithPersona = async (personaId) => {
  selectedPersona.value = personaId
  localStorage.setItem('sr_last_persona', personaId)
  showPersonaPicker.value = false
  saveSession(currentUser.value, personaId)
  await initChat()
}

// ============================================================
// Task 5: send() — 消息聚合入口（防抖队列）
// ============================================================
// ============================================================
// 图片上传处理
// ============================================================
const handleImageUpload = (e) => {
  const file = e.target.files[0]
  if (!file) return

  // 限制只能上传图片
  if (!file.type.startsWith('image/')) {
    alert('只能上传图片文件（支持 JPG、PNG、GIF、WebP 等格式）')
    e.target.value = ''
    return
  }

  imageMimeType.value = file.type
  const reader = new FileReader()
  reader.onload = () => {
    const base64 = reader.result.split(',')[1]
    imageBase64.value = base64
    imagePreview.value = reader.result
  }
  reader.readAsDataURL(file)
}

const clearImage = () => {
  imageBase64.value = null
  imagePreview.value = null
  imageMimeType.value = 'image/png'
}

const send = async () => {
  if (!inputText.value.trim() && !imageBase64.value) return
  if (!apiConfigured.value) { showSettings.value = true; return }

  const text = inputText.value.trim()
  inputText.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'

  // 保存并清除图片
  const img = imageBase64.value
  const imgPreview = imagePreview.value
  imageBase64.value = null
  imagePreview.value = null

  // 立即将用户消息推入聊天列表（即时视觉反馈）
  const userMsg = {
    _id: Date.now(),
    content: text || '[图片]',
    senderId: 'user',
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    status: 'sent',
    image: imgPreview || undefined
  }
  messages.value.push(userMsg)
  scrollEnd()

  setTimeout(() => {
    const i = messages.value.findIndex(m => m._id === userMsg._id)
    if (i !== -1) messages.value[i].status = 'delivered'
  }, 400)

  // Task 4: 中断正在进行的 AI 分段播放
  playbackInterrupted.value = true

  // 有图片时立即发送，不入聚合队列
  if (img) {
    // 清空已有队列
    if (pendingQueue.value.length > 0) {
      flushQueue()
    }
    doSend(text, img)
    return
  }

  // Task 5: 推入聚合队列
  pendingQueue.value.push(text)
  showSendNow.value = true

  // AI 正在回复时，暂停聚合发送——仅入队，等 aiTyping 结束后 auto-flush
  if (aiTyping.value) return

  // 重置 3 秒聚合计时器
  if (aggregateTimer.value) {
    clearTimeout(aggregateTimer.value)
  }
  aggregateTimer.value = setTimeout(() => {
    flushQueue()
  }, 3000)
}

// ============================================================
// Task 5: flushQueue() — 聚合队列发送
// ============================================================
const flushQueue = () => {
  if (pendingQueue.value.length === 0) return
  if (aggregateTimer.value) {
    clearTimeout(aggregateTimer.value)
    aggregateTimer.value = null
  }
  const combinedText = pendingQueue.value.join('\n')
  pendingQueue.value = []
  showSendNow.value = false
  doSend(combinedText)
}

// ============================================================
// Task 5: sendNow() — "立即发送"按钮回调
// ============================================================
const sendNow = () => {
  flushQueue()
}

// ============================================================
// Task 4 & Task 6: doSend() — 实际 HTTP 请求 + 分段渲染
// ============================================================
const doSend = async (combinedText, imageData = null) => {
  if (aiTyping.value) return

  aiTyping.value = true

  try {
    const body = {
      persona_id: selectedPersona.value,
      message: combinedText,
      user_is_typing: userTyping.value
    }
    if (imageData) {
      body.image_base64 = imageData
      body.image_mime_type = imageMimeType.value
    }
    const r = await apiFetch(`${API}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const d = await r.json()

    // ============================================================
    // Task 4: 分段渲染
    // ============================================================
    if (d.segments && d.segments.length > 0) {
      // 空消息兜底：若 AI 返回空内容，替换为默认提示
      const firstContent = (d.segments[0] && d.segments[0].trim()) ? d.segments[0] : '（AI 暂时无法回应，请稍后再试）'
      const aiMsg = {
        _id: Date.now(),
        content: firstContent,
        senderId: 'ai',
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        busy: d.ai_message?.busy || false,
        cooling: d.ai_message?.cooling || false,
        breakup: d.ai_message?.breakup || false,
        restart: d.ai_message?.restart || false,
        emojis: d.emojis || []
      }

      if (d.ai_message?.busy) aiBusyState.value = true
      if (d.ai_message?.cooling) aiCoolingState.value = true
      if (d.ai_message?.restart) { aiCoolingState.value = false; aiBusyState.value = false }
      if (d.ai_message?.breakup) { aiCoolingState.value = true; aiBusyState.value = false }
      messages.value.push(aiMsg)
      scrollEnd()

      // 重置中断标志
      playbackInterrupted.value = false

      // 多段：逐段追加渲染
      if (d.segments.length > 1 && d.delays) {
        for (let i = 1; i < d.segments.length; i++) {
          // 检查是否被中断（用户在此期间发了新消息）
          if (playbackInterrupted.value) {
            aiMsg.content += d.segments.slice(i).join('')
            scrollEnd()
            break
          }

          // 模拟自然停顿
          await new Promise(resolve => setTimeout(resolve, d.delays[i] || 1500))

          // 等待后再检查一次中断
          if (playbackInterrupted.value) {
            aiMsg.content += d.segments.slice(i).join('')
            scrollEnd()
            break
          }

          // 追加下一段文本
          aiMsg.content += d.segments[i]
          scrollEnd()
        }
      }
    } else if (d.ai_message) {
      // 兼容旧版响应（无 segments 字段）
      if (!d.ai_message.content || !d.ai_message.content.trim()) {
        d.ai_message.content = '（AI 暂时无法回应，请稍后再试）'
      }
      messages.value.push(d.ai_message)
    }

    if (d.monologue) {
      monologueData.value = d.monologue
    }

    // 将所有待处理的用户消息标记为已读
    messages.value.forEach(m => {
      if (m.senderId === 'user' && m.status !== 'read') {
        m.status = 'read'
      }
    })

    if (d.agent) {
      currentPhase.value = d.agent.phase || currentPhase.value
      relationshipDays.value = d.agent.relationship_days || relationshipDays.value
      intimacy.value = d.agent.intimacy ?? intimacy.value
      passion.value = d.agent.passion ?? passion.value
      commitment.value = d.agent.commitment ?? commitment.value
    }
    if (d.shared_memories) {
      milestones.value = d.shared_memories.milestones || milestones.value
      promises.value = d.shared_memories.important_promises || promises.value
    }
    if (d.memu_status) {
      memuStatus.value = d.memu_status
    }
    scrollEnd()
  } catch (e) {
    logError('send', e.message, e.stack)
    messages.value.push({
      _id: Date.now(),
      content: '连接后端失败，请确保后端服务已启动',
      senderId: 'ai',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })
    scrollEnd()
  } finally {
    aiTyping.value = false

    // Task 5: AI 回复完成后，若队列中还有待发消息，自动 flush
    if (pendingQueue.value.length > 0) {
      nextTick(() => flushQueue())
    }
  }
}

watch(selectedPersona, (val) => {
  localStorage.setItem('sr_last_persona', val)
  if (val && currentUser.value) {
    saveSession(currentUser.value, val)
  }
  if (val) loadMessages()
})

watch(showMemory, (val) => {
  if (val) loadMemory()
})

watch([isLoggedIn, selectedPersona], ([loggedIn, persona]) => {
  if (loggedIn && !persona && !showPersonaPicker.value) {
    showPersonaPicker.value = true
  }
})

// Task 6: 监听输入框内容，更新 userTyping 状态
watch(inputText, (val) => {
  userTyping.value = val.trim().length > 0
})

const priColor = (p) => {
  if (p >= 8) return '#ef4444'
  if (p >= 6) return '#f59e0b'
  if (p >= 4) return '#6366f1'
  return '#64748b'
}

const initChat = async () => {
  await checkConfig()
  await loadMessages()
  if (messages.value.length === 0) {
    messages.value = [
      { _id: 1, content: '嗨，你好呀～', senderId: 'ai', timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
    ]
  }
  scrollEnd()
}

onMounted(async () => {
  window.onerror = (msg, url, line, col, error) => {
    logError('window.onerror', `${msg} at ${url}:${line}:${col}`, error?.stack)
    return false
  }
  window.onunhandledrejection = (event) => {
    logError('unhandledrejection', event.reason?.message || String(event.reason), event.reason?.stack)
  }

  loadRecentUsers()
  await checkConfig()
  await loadPersonas()

  setInterval(async () => {
    if (!currentUser.value || !selectedPersona.value) return
    try {
      const r = await apiFetch(`${API}/api/check-proactive?persona_id=${selectedPersona.value}`)
      const d = await r.json()
      if (d.type && d.message) {
        const msgId = d._id
        if (msgId && messages.value.some(m => m._id === msgId)) return
        aiTyping.value = true
        await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 1500))
        aiTyping.value = false
        const msgContent = typeof d.message === 'string' ? d.message : d.message.content
        const proactiveMsg = {
          _id: msgId || Date.now(),
          content: msgContent,
          senderId: 'ai',
          timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
          proactive: true
        }
        messages.value.push(proactiveMsg)
        scrollEnd()
      }
    } catch (e) {
        if (e.message !== 'UNAUTHORIZED') logError('proactive-poll', e.message, e.stack)
      }
  }, 10000)

  const session = loadSession()
  if (session && getAuthToken()) {
    try {
      const r = await apiFetch(`${API}/api/users/me`)
      if (!r.ok) {
        clearSession()
        currentUser.value = null
        return
      }
      const me = await r.json()
      if (me.token) localStorage.setItem(TOKEN_KEY, me.token)
    } catch (e) {
      if (e.message !== 'UNAUTHORIZED') logError('session-restore', e.message, e.stack)
      clearSession()
      currentUser.value = null
      return
    }
    currentUser.value = session.username
    loadUserSettings()
    if (session.username === 'admin888') {
      showPersonaPicker.value = false
      await adminLoadUsers()
      adminLoadVisionModelConfig()
    } else if (session.persona && personas.value.some(p => p.id === session.persona)) {
      selectedPersona.value = session.persona
      showPersonaPicker.value = false
      try {
        await initChat()
      } catch (e) {
        logError('initChat-onMount', e.message, e.stack)
      }
      if (!hasCurrentAgent.value && messages.value.length === 0) {
        localStorage.removeItem('sr_last_persona')
        selectedPersona.value = ''
        showPersonaPicker.value = true
      }
    } else {
      selectedPersona.value = ''
      showPersonaPicker.value = true
    }
    return
  }

  if (!localStorage.getItem('sr_agreed')) {
    showAgreement.value = true
    return
  }

  const lastUser = localStorage.getItem('sr_last_user')
  if (lastUser) {
    loginUsername.value = lastUser
    nextTick(() => loginPwRef.value?.focus())
  }
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}

:root {
  --font: 'Noto Sans SC', -apple-system, sans-serif;
  --warm-1: #fef3e2;
  --warm-2: #fde8c8;
  --warm-accent: #e0915a;
  --warm-accent2: #c97b4a;
  --warm-rose: #e8a0a0;
  --warm-rose2: #d47878;
  --night-1: #12111a;
  --night-2: #1c1a28;
  --night-3: #262336;
  --night-accent: #c9976e;
  --night-accent2: #a87d5a;
  --night-rose: #b87878;
  --night-text: #ede8e2;
  --night-muted: #7a7586;
  --radius: 18px;
  --radius-sm: 12px;
  --ease: cubic-bezier(.4,0,.2,1);
}

body { font-family: var(--font); -webkit-font-smoothing: antialiased }

.app { min-height: 100vh; position: relative; overflow: hidden }
.app.dark { background: var(--night-1); color: var(--night-text) }
.app.light { background: var(--warm-1); color: #3d2e1e }

.ambient-layer { position: fixed; inset: 0; pointer-events: none; z-index: 0 }
.glow { position: absolute; border-radius: 50%; filter: blur(80px) }

.dark .glow-1 { width: 400px; height: 400px; top: -100px; left: -80px; background: rgba(201,151,110,.08) }
.dark .glow-2 { width: 350px; height: 350px; bottom: -80px; right: -60px; background: rgba(184,120,120,.06) }
.light .glow-1 { width: 400px; height: 400px; top: -100px; left: -80px; background: rgba(224,145,90,.1) }
.light .glow-2 { width: 350px; height: 350px; bottom: -80px; right: -60px; background: rgba(232,160,160,.08) }

.grain { position: absolute; inset: 0; opacity: .03; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E") }

.shell { position: relative; z-index: 1; max-width: 460px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column }

.topbar { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); flex-shrink: 0 }
.dark .topbar { background: rgba(18,17,26,.75); border-bottom: 1px solid rgba(255,255,255,.04) }
.light .topbar { background: rgba(254,243,226,.75); border-bottom: 1px solid rgba(0,0,0,.05) }

.ai-presence { display: flex; align-items: center; gap: 10px; cursor: pointer; transition: opacity .2s var(--ease) }
.ai-presence:hover { opacity: .85 }

.ai-ring { position: relative; width: 38px; height: 38px; border-radius: 50%; padding: 2px; flex-shrink: 0 }
.dark .ai-ring { background: linear-gradient(135deg, var(--night-accent), var(--night-rose)) }
.light .ai-ring { background: linear-gradient(135deg, var(--warm-accent), var(--warm-rose)) }
.ai-ring img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover }
.dark .ai-ring img { border: 2px solid var(--night-1) }
.light .ai-ring img { border: 2px solid var(--warm-1) }

.online-dot { position: absolute; bottom: 0; right: 0; width: 10px; height: 10px; border-radius: 50%; background: #4ade80; animation: pulse-dot 2s infinite }
.dark .online-dot { border: 2px solid var(--night-1) }
.light .online-dot { border: 2px solid var(--warm-1) }

@keyframes pulse-dot { 0%,100%{ box-shadow: 0 0 0 0 rgba(74,222,128,.4) } 50%{ box-shadow: 0 0 0 4px rgba(74,222,128,0) } }

.ai-info { display: flex; flex-direction: column; gap: 1px }
.ai-name { font-size: 14px; font-weight: 600; letter-spacing: -.01em }
.ai-status { font-size: 11px; color: #4ade80 }

.topbar-center { position: absolute; left: 50%; transform: translateX(-50%) }
.phase-pill { display: flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 99px; font-size: 11px; font-weight: 500 }
.dark .phase-pill { background: rgba(201,151,110,.12); color: var(--night-accent) }
.light .phase-pill { background: rgba(224,145,90,.12); color: var(--warm-accent2) }
.phase-sep { opacity: .4 }

.topbar-right { display: flex; gap: 2px }
.tb-btn { width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border: none; border-radius: 10px; cursor: pointer; transition: all .2s var(--ease); background: transparent }
.dark .tb-btn { color: var(--night-muted) }
.light .tb-btn { color: #9a8a7a }
.dark .tb-btn:hover { background: rgba(201,151,110,.1); color: var(--night-accent) }
.light .tb-btn:hover { background: rgba(224,145,90,.1); color: var(--warm-accent) }
.tb-btn svg { width: 18px; height: 18px }

.chat-body { flex: 1; overflow-y: auto; padding: 12px 16px; scroll-behavior: smooth }
.chat-body::-webkit-scrollbar { width: 3px }
.chat-body::-webkit-scrollbar-thumb { border-radius: 3px }
.dark .chat-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08) }
.light .chat-body::-webkit-scrollbar-thumb { background: rgba(0,0,0,.08) }

.msg-list { display: flex; flex-direction: column; gap: 6px }

.load-more-row { display: flex; justify-content: center; padding: 8px 0 }
.load-more-btn {
  font-size: 12px; padding: 6px 16px; border-radius: 99px; border: 1px solid;
  cursor: pointer; transition: all .2s var(--ease); background: transparent;
}
.dark .load-more-btn { color: var(--night-muted); border-color: rgba(255,255,255,.1) }
.dark .load-more-btn:hover { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.2) }
.light .load-more-btn { color: #9a8a7a; border-color: rgba(0,0,0,.08) }
.light .load-more-btn:hover { background: rgba(0,0,0,.03); border-color: rgba(0,0,0,.15) }
.load-more-btn:disabled { opacity: .5; cursor: not-allowed }

.date-tag { display: flex; justify-content: center; padding: 12px 0 8px }
.date-tag span { font-size: 11px; padding: 3px 12px; border-radius: 99px }
.dark .date-tag span { background: rgba(255,255,255,.04); color: var(--night-muted) }
.light .date-tag span { background: rgba(0,0,0,.04); color: #9a8a7a }

.msg { display: flex; align-items: flex-end; gap: 8px; max-width: 82%; animation: msg-in .3s var(--ease) }
.msg-ai { align-self: flex-start }
.msg-self { align-self: flex-end; flex-direction: row-reverse }

@keyframes msg-in { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: translateY(0) } }

.msg-avatar { width: 30px; height: 30px; border-radius: 50%; overflow: hidden; flex-shrink: 0 }
.msg-avatar img { width: 100%; height: 100%; object-fit: cover }

.msg-body { display: flex; flex-direction: column; gap: 3px }
.msg-self .msg-body { align-items: flex-end }

.msg-bubble { padding: 10px 14px; border-radius: var(--radius); font-size: 0.875rem; line-height: 1.6 }
.msg-ai .msg-bubble { border-top-left-radius: 4px }
.msg-self .msg-bubble { border-top-right-radius: 4px }

.dark .msg-ai .msg-bubble { background: var(--night-3); color: var(--night-text) }
.light .msg-ai .msg-bubble { background: #fff; color: #3d2e1e; box-shadow: 0 1px 4px rgba(0,0,0,.04) }

.dark .msg-self .msg-bubble { background: linear-gradient(135deg, var(--night-accent), var(--night-accent2)); color: #1a1510 }
.light .msg-self .msg-bubble { background: linear-gradient(135deg, var(--warm-accent), var(--warm-accent2)); color: #fff }

.msg-bubble p { margin: 0; word-break: break-word }

.msg-foot { display: flex; align-items: center; gap: 4px; font-size: 10px; padding: 0 4px }
.dark .msg-foot { color: var(--night-muted) }
.light .msg-foot { color: #b0a090 }

.msg-check svg { width: 14px; height: 10px; opacity: .5 }
.msg-check .read { opacity: 1 }
.dark .msg-check .read { color: var(--night-accent) }
.light .msg-check .read { color: var(--warm-accent) }

.typing-row { display: flex; align-items: flex-end; gap: 8px; padding: 4px 0 }
.typing-bubble { display: flex; gap: 4px; padding: 12px 16px; border-radius: var(--radius); border-top-left-radius: 4px }
.dark .typing-bubble { background: var(--night-3) }
.light .typing-bubble { background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.04) }
.typing-bubble span { width: 6px; height: 6px; border-radius: 50%; animation: bounce 1.4s infinite }
.dark .typing-bubble span { background: var(--night-muted) }
.light .typing-bubble span { background: #c0b0a0 }
.typing-bubble span:nth-child(2) { animation-delay: .15s }
.typing-bubble span:nth-child(3) { animation-delay: .3s }
@keyframes bounce { 0%,60%,100%{ transform: translateY(0); opacity:.4 } 30%{ transform: translateY(-5px); opacity:1 } }

.typing-fade-enter-active,.typing-fade-leave-active { transition: all .25s var(--ease) }
.typing-fade-enter-from,.typing-fade-leave-to { opacity: 0; transform: translateY(6px) }

.input-dock { padding: 8px 16px 16px; backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); flex-shrink: 0 }
.dark .input-dock { background: rgba(18,17,26,.7); border-top: 1px solid rgba(255,255,255,.04) }
.light .input-dock { background: rgba(254,243,226,.7); border-top: 1px solid rgba(0,0,0,.05) }

.input-shell { display: flex; align-items: flex-end; gap: 8px; padding: 8px 12px; border-radius: var(--radius); transition: all .2s var(--ease) }
.dark .input-shell { background: var(--night-3); border: 1px solid rgba(255,255,255,.05) }
.light .input-shell { background: #fff; border: 1px solid rgba(0,0,0,.06); box-shadow: 0 1px 4px rgba(0,0,0,.03) }
.input-shell:focus-within { border-color: transparent }
.dark .input-shell:focus-within { box-shadow: 0 0 0 2px var(--night-accent) }
.light .input-shell:focus-within { box-shadow: 0 0 0 2px var(--warm-accent) }

.input-shell textarea { flex: 1; border: none; background: transparent; font-family: inherit; font-size: 0.875rem; line-height: 1.5; resize: none; min-height: 22px; max-height: 120px; outline: none; color: inherit }
.dark .input-shell textarea::placeholder { color: var(--night-muted) }
.light .input-shell textarea::placeholder { color: #b0a090 }

.send { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: none; border-radius: 50%; cursor: pointer; transition: all .2s var(--ease); flex-shrink: 0 }
.send svg { width: 16px; height: 16px }
.dark .send { background: var(--night-muted); color: var(--night-1) }
.light .send { background: #c0b0a0; color: #fff }
.dark .send.on { background: var(--night-accent) }
.light .send.on { background: var(--warm-accent) }
.send:disabled { opacity: .4; cursor: not-allowed }

/* Task 5: "立即发送"按钮 */
.send-now-btn {
  padding: 6px 12px;
  border-radius: 10px;
  border: none;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all .25s var(--ease);
  white-space: nowrap;
  flex-shrink: 0;
}
.dark .send-now-btn { background: var(--night-accent); color: #1a1510; }
.light .send-now-btn { background: var(--warm-accent); color: #fff; }
.send-now-btn:hover:not(:disabled) { filter: brightness(1.08); }
.send-now-btn:disabled { opacity: .4; cursor: not-allowed; }

/* 图片上传按钮 */
.img-upload-btn {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; cursor: pointer; transition: all .2s var(--ease); flex-shrink: 0;
}
.img-upload-btn svg { width: 16px; height: 16px; }
.dark .img-upload-btn { background: transparent; color: var(--night-muted); }
.light .img-upload-btn { background: transparent; color: #b0a090; }
.img-upload-btn:hover { opacity: .8; }

/* 图片预览条 */
.image-preview-bar {
  display: flex; align-items: center; gap: 8px; padding: 6px 12px;
  border-radius: var(--radius) var(--radius) 0 0; flex-shrink: 0;
}
.dark .image-preview-bar { background: var(--night-3); border-bottom: 1px solid rgba(255,255,255,.05); }
.light .image-preview-bar { background: #fff; border-bottom: 1px solid rgba(0,0,0,.06); }
.image-preview-thumb { max-height: 80px; max-width: 120px; border-radius: 8px; object-fit: cover; }
.image-preview-remove {
  width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; cursor: pointer; font-size: 12px;
}
.dark .image-preview-remove { background: rgba(255,255,255,.1); color: #fff; }
.light .image-preview-remove { background: rgba(0,0,0,.1); color: #333; }

/* 表情包展示 */
.msg-emoji-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.msg-emoji-img { max-width: 120px; max-height: 120px; border-radius: 8px; object-fit: contain; }

/* 用户消息中的图片 */
.msg-image-wrap { margin-top: 6px; }
.msg-image-thumb { max-width: 200px; max-height: 200px; border-radius: 10px; object-fit: cover; }

.triangle-bar { display: flex; justify-content: center; gap: 28px; padding: 10px 16px; backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); flex-shrink: 0 }
.dark .triangle-bar { background: rgba(18,17,26,.7); border-top: 1px solid rgba(255,255,255,.04) }
.light .triangle-bar { background: rgba(254,243,226,.7); border-top: 1px solid rgba(0,0,0,.05) }

.tri-item { display: flex; flex-direction: column; align-items: center; gap: 4px }
.tri-ring { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; position: relative; background: conic-gradient(currentColor var(--pct), transparent var(--pct)) }
.tri-ring::after { content: ''; position: absolute; inset: 3px; border-radius: 50% }
.dark .tri-ring::after { background: var(--night-1) }
.light .tri-ring::after { background: var(--warm-1) }
.tri-val { position: relative; z-index: 1; font-size: 12px; font-weight: 700 }
.tri-item.intimacy { color: #f472b6 }
.tri-item.passion { color: #fb7185 }
.tri-item.commitment { color: #a78bfa }
.tri-label { font-size: 10px }
.dark .tri-label { color: var(--night-muted) }
.light .tri-label { color: #9a8a7a }

.slide-up-enter-active,.slide-up-leave-active { transition: all .25s var(--ease) }
.slide-up-enter-from,.slide-up-leave-to { opacity: 0; transform: translateY(10px) }

.overlay { position: fixed; inset: 0; z-index: 100; display: flex; align-items: flex-end; justify-content: center; padding: 0 16px 0 }
.dark .overlay { background: rgba(0,0,0,.5) }
.light .overlay { background: rgba(0,0,0,.25) }

.overlay-center { align-items: center; padding: 24px 16px }
.overlay-center .panel { border-radius: var(--radius); animation: panel-center .3s var(--ease) }
@keyframes panel-center { from { transform: scale(.94); opacity: 0 } to { transform: scale(1); opacity: 1 } }

.overlay-enter-active,.overlay-leave-active { transition: all .25s var(--ease) }
.overlay-enter-from,.overlay-leave-to { opacity: 0 }

.panel { width: 100%; max-width: 460px; max-height: 85vh; border-radius: var(--radius) var(--radius) 0 0; overflow-y: auto; animation: panel-up .3s var(--ease); scrollbar-width: thin }
.dark .panel { background: var(--night-2) }
.light .panel { background: #fff }

.panel::-webkit-scrollbar { width: 4px }
.panel::-webkit-scrollbar-track { background: transparent }
.dark .panel::-webkit-scrollbar-thumb { background: rgba(255,255,255,.1); border-radius: 4px }
.light .panel::-webkit-scrollbar-thumb { background: rgba(0,0,0,.1); border-radius: 4px }
.dark .panel::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.18) }
.light .panel::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,.18) }
.dark .panel { scrollbar-color: rgba(255,255,255,.1) transparent }
.light .panel { scrollbar-color: rgba(0,0,0,.1) transparent }

@keyframes panel-up { from { transform: translateY(20px); opacity: 0 } to { transform: translateY(0); opacity: 1 } }

.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px }
.dark .panel-head { border-bottom: 1px solid rgba(255,255,255,.05) }
.light .panel-head { border-bottom: 1px solid rgba(0,0,0,.06) }
.panel-head h3 { font-size: 1rem; font-weight: 600 }
.panel-close-btn { width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; background: transparent; color: inherit; transition: background .2s; }
.dark .panel-close-btn:hover { background: rgba(255,255,255,.08); }
.light .panel-close-btn:hover { background: rgba(0,0,0,.06); }

.x-btn { width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border: none; border-radius: 50%; cursor: pointer; background: transparent; transition: all .2s var(--ease) }
.dark .x-btn { color: var(--night-muted) }
.light .x-btn { color: #9a8a7a }
.dark .x-btn:hover { background: rgba(255,255,255,.06) }
.light .x-btn:hover { background: rgba(0,0,0,.05) }
.x-btn svg { width: 16px; height: 16px }

.panel-block { padding: 16px 20px }
.dark .panel-block + .panel-block { border-top: 1px solid rgba(255,255,255,.05) }
.light .panel-block + .panel-block { border-top: 1px solid rgba(0,0,0,.06) }
.panel-block h4 { font-size: 0.75rem; font-weight: 500; margin-bottom: 12px }
.dark .panel-block h4 { color: var(--night-muted) }
.light .panel-block h4 { color: #9a8a7a }

.persona-list { display: flex; flex-direction: column; gap: 8px }
.persona-chip { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border: none; border-radius: var(--radius-sm); cursor: pointer; transition: all .2s var(--ease); font-family: inherit; text-align: left }
.dark .persona-chip { background: var(--night-3) }
.light .persona-chip { background: var(--warm-1) }
.dark .persona-chip:hover { background: rgba(201,151,110,.1) }
.light .persona-chip:hover { background: rgba(224,145,90,.08) }
.dark .persona-chip.picked { background: rgba(201,151,110,.15); outline: 2px solid var(--night-accent) }
.light .persona-chip.picked { background: rgba(224,145,90,.12); outline: 2px solid var(--warm-accent) }
.persona-chip img { width: 36px; height: 36px; border-radius: 50% }
.chip-text { display: flex; flex-direction: column; gap: 1px }
.chip-name { font-size: 13px; font-weight: 500 }
.chip-type { font-size: 11px }
.dark .chip-type { color: var(--night-muted) }
.light .chip-type { color: #9a8a7a }

.theme-row { display: flex; gap: 8px }
.theme-opt { flex: 1; padding: 10px; border: none; border-radius: var(--radius-sm); cursor: pointer; font-family: inherit; font-size: 13px; transition: all .2s var(--ease) }
.dark .theme-opt { background: var(--night-3); color: var(--night-muted) }
.light .theme-opt { background: var(--warm-1); color: #9a8a7a }
.dark .theme-opt.on { background: rgba(201,151,110,.15); color: var(--night-accent) }
.light .theme-opt.on { background: rgba(224,145,90,.12); color: var(--warm-accent) }

.config-form { display: flex; flex-direction: column; gap: 8px }
.config-input { padding: 10px 12px; border: none; border-radius: var(--radius-sm); font-family: inherit; font-size: 0.8125rem; outline: none }
.dark .config-input { background: var(--night-3); color: var(--night-text); border: 1px solid rgba(255,255,255,.06) }
.light .config-input { background: var(--warm-1); color: #3d2e1e; border: 1px solid rgba(0,0,0,.06) }
.config-input:focus { border-color: transparent }
.dark .config-input:focus { box-shadow: 0 0 0 2px var(--night-accent) }
.light .config-input:focus { box-shadow: 0 0 0 2px var(--warm-accent) }
.config-btn { padding: 10px; border: none; border-radius: var(--radius-sm); cursor: pointer; font-family: inherit; font-size: 0.8125rem; font-weight: 500; transition: all .2s var(--ease) }
.dark .config-btn { background: var(--night-accent); color: #1a1510 }
.light .config-btn { background: var(--warm-accent); color: #fff }
.config-btn:disabled { opacity: .5; cursor: not-allowed }
.config-msg { font-size: 12px; margin-top: 4px }

.profile-panel { padding: 0 }
.profile-hero { height: 140px; background-size: cover; background-position: center; position: relative }
.profile-hero-overlay { position: absolute; inset: 0 }
.dark .profile-hero-overlay { background: linear-gradient(transparent 30%, var(--night-2)) }
.light .profile-hero-overlay { background: linear-gradient(transparent 30%, #fff) }
.profile-hero .x-btn { position: absolute; top: 12px; right: 12px; z-index: 2 }
.dark .profile-hero .x-btn { color: #fff }
.light .profile-hero .x-btn { color: #fff }

.profile-body { padding: 0 24px 28px; text-align: center; margin-top: -32px; position: relative }
.profile-avatar { width: 64px; height: 64px; border-radius: 50%; border: 3px solid }
.dark .profile-avatar { border-color: var(--night-2) }
.light .profile-avatar { border-color: #fff }
.profile-body h2 { font-size: 18px; font-weight: 600; margin-top: 8px }
.profile-tag { font-size: 12px; margin-top: 2px }
.dark .profile-tag { color: var(--night-muted) }
.light .profile-tag { color: #9a8a7a }
.profile-bio { font-size: 13px; line-height: 1.6; margin-top: 10px }
.dark .profile-bio { color: var(--night-muted) }
.light .profile-bio { color: #7a6a5a }

.profile-stats { display: flex; justify-content: center; gap: 32px; margin-top: 18px }
.stat { display: flex; flex-direction: column; align-items: center; gap: 2px }
.stat-num { font-size: 16px; font-weight: 700 }
.dark .stat-num { color: var(--night-accent) }
.light .stat-num { color: var(--warm-accent) }
.stat-lbl { font-size: 10px }
.dark .stat-lbl { color: var(--night-muted) }
.light .stat-lbl { color: #9a8a7a }

.memu-stats { display: flex; justify-content: center; gap: 24px }
.memu-stat-item { display: flex; flex-direction: column; align-items: center; gap: 2px }
.memu-stat-num { font-size: 18px; font-weight: 700 }
.dark .memu-stat-num { color: var(--night-accent) }
.light .memu-stat-num { color: var(--warm-accent) }
.memu-stat-lbl { font-size: 10px }
.dark .memu-stat-lbl { color: var(--night-muted) }
.light .memu-stat-lbl { color: #9a8a7a }

.memu-empty { text-align: center; padding: 12px 0 }
.memu-empty p { font-size: 13px }
.dark .memu-empty p { color: var(--night-muted) }
.light .memu-empty p { color: #9a8a7a }

.memu-cat-list { display: flex; flex-direction: column; gap: 8px }
.memu-cat { border-radius: var(--radius-sm); padding: 10px 12px }
.dark .memu-cat { background: var(--night-3) }
.light .memu-cat { background: var(--warm-1) }
.memu-cat-head { display: flex; justify-content: space-between; align-items: center }
.memu-cat-name { font-size: 13px; font-weight: 500 }
.memu-cat-count { font-size: 11px }
.dark .memu-cat-count { color: var(--night-accent) }
.light .memu-cat-count { color: var(--warm-accent) }
.memu-cat-summary { font-size: 11px; margin-top: 4px; line-height: 1.4 }
.dark .memu-cat-summary { color: var(--night-muted) }
.light .memu-cat-summary { color: #9a8a7a }
.memu-cat-meta { display: flex; gap: 12px; margin-top: 6px }
.memu-cat-meta span { font-size: 10px }
.dark .memu-cat-meta span { color: var(--night-muted) }
.light .memu-cat-meta span { color: #9a8a7a }

.milestone-list { display: flex; flex-direction: column; gap: 8px }
.milestone { display: flex; align-items: center; gap: 10px }
.ms-icon { font-size: 16px; flex-shrink: 0 }
.ms-body { display: flex; flex-direction: column; gap: 1px }
.ms-label { font-size: 13px; font-weight: 500 }
.ms-date { font-size: 10px }
.dark .ms-date { color: var(--night-muted) }
.light .ms-date { color: #9a8a7a }

.promise-list { display: flex; flex-direction: column; gap: 6px }
.promise { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-radius: var(--radius-sm) }
.dark .promise { background: var(--night-3) }
.light .promise { background: var(--warm-1) }
.promise-text { font-size: 12px }
.promise-date { font-size: 10px }
.dark .promise-date { color: var(--night-muted) }
.light .promise-date { color: #9a8a7a }

.monologue-bar {
  padding: 12px 16px;
  margin: 0 12px 8px;
  border-radius: var(--radius);
  font-size: 12px;
  line-height: 1.5;
}
.dark .monologue-bar { background: rgba(201, 151, 110, 0.08); border: 1px solid rgba(201, 151, 110, 0.15); }
.light .monologue-bar { background: rgba(224, 145, 90, 0.06); border: 1px solid rgba(224, 145, 90, 0.1); }
.monologue-bar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-weight: 600; }
.monologue-emotion { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.dark .monologue-emotion { background: rgba(201, 151, 110, 0.15); color: var(--night-accent); }
.light .monologue-emotion { background: rgba(224, 145, 90, 0.12); color: var(--warm-accent); }
.monologue-bar-reasoning { margin-bottom: 6px; }
.dark .monologue-bar-reasoning { color: var(--night-muted); }
.light .monologue-bar-reasoning { color: #7a6a5a; }
.monologue-bar-meta { display: flex; gap: 12px; font-size: 10px; margin-bottom: 6px; }
.dark .monologue-bar-meta { color: var(--night-muted); }
.light .monologue-bar-meta { color: #9a8a7a; }
.monologue-bar-obs { display: flex; flex-wrap: wrap; gap: 4px; }
.monologue-obs-tag { font-size: 10px; padding: 1px 6px; border-radius: 8px; }
.dark .monologue-obs-tag { background: rgba(255,255,255,0.04); color: var(--night-muted); }
.light .monologue-obs-tag { background: rgba(0,0,0,0.04); color: #9a8a7a; }

.tb-btn.active svg { stroke-width: 2; }
.dark .tb-btn.active { color: var(--night-accent); background: rgba(201,151,110,.15); }
.light .tb-btn.active { color: var(--warm-accent); background: rgba(224,145,90,.12); }

@media (max-width: 480px) {
  .shell { max-width: 100% }
  .topbar-center { display: none }
}

.login-screen { position: fixed; inset: 0; z-index: 10; display: flex; align-items: center; justify-content: center; padding: 24px; }
.login-card { position: relative; z-index: 2; width: 100%; max-width: 360px; animation: login-in .6s var(--ease); }
@keyframes login-in { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

.login-logo { text-align: center; margin-bottom: 32px; }
.login-emoji { font-size: 48px; margin-bottom: 8px; }
.login-title { font-size: 24px; font-weight: 700; letter-spacing: .02em; margin-bottom: 4px; }
.dark .login-title { color: var(--night-text); }
.light .login-title { color: #3d2e1e; }
.login-slogan { font-size: 13px; }
.dark .login-slogan { color: var(--night-muted); }
.light .login-slogan { color: #9a8a7a; }

.login-form { display: flex; flex-direction: column; gap: 12px; }
.login-input-wrap { position: relative; }
.login-input { width: 100%; padding: 14px 16px; border-radius: 16px; font-family: inherit; font-size: 16px; text-align: center; outline: none; border: 1px solid transparent; transition: all .25s var(--ease); }
.dark .login-input { background: rgba(38,35,54,.7); color: var(--night-text); border-color: rgba(255,255,255,.08); backdrop-filter: blur(12px); }
.light .login-input { background: rgba(255,255,255,.7); color: #3d2e1e; border-color: rgba(0,0,0,.08); backdrop-filter: blur(12px); }
.dark .login-input::placeholder { color: rgba(255,255,255,.25); }
.light .login-input::placeholder { color: rgba(0,0,0,.25); }
.dark .login-input:focus { border-color: var(--night-accent); box-shadow: 0 0 0 3px rgba(201,151,110,.12); }
.light .login-input:focus { border-color: var(--warm-accent); box-shadow: 0 0 0 3px rgba(224,145,90,.12); }

.login-actions { display: flex; gap: 10px; }
.login-btn { flex: 1; padding: 14px; border-radius: 16px; border: none; font-family: inherit; font-size: 16px; font-weight: 600; cursor: pointer; transition: all .25s var(--ease); }
.dark .login-btn { background: var(--night-accent); color: #1a1510; }
.light .login-btn { background: var(--warm-accent); color: #fff; }
.login-btn:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); }
.login-btn:disabled { opacity: .5; cursor: not-allowed; }
.login-btn-register, .login-btn-back { background: transparent !important; border: 1px solid !important; }
.dark .login-btn-register, .dark .login-btn-back { color: var(--night-accent); border-color: var(--night-accent) !important; }
.light .login-btn-register, .light .login-btn-back { color: var(--warm-accent); border-color: var(--warm-accent) !important; }

.login-msg { text-align: center; font-size: 12px; }
.dark .login-msg { color: var(--night-muted); }
.light .login-msg { color: #9a8a7a; }

.login-forgot { text-align: center; font-size: 13px; margin-top: 2px; }
.login-forgot a { text-decoration: none; opacity: .6; transition: opacity .2s; }
.login-forgot a:hover { opacity: 1; }
.dark .login-forgot a { color: var(--night-accent); }
.light .login-forgot a { color: var(--warm-accent); }

.login-recent { margin-top: 32px; text-align: center; }
.login-recent-title { font-size: 11px; margin-bottom: 10px; }
.dark .login-recent-title { color: var(--night-muted); }
.light .login-recent-title { color: #9a8a7a; }
.login-recent-list { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.login-recent-chip { padding: 8px 16px; border-radius: 99px; border: none; font-family: inherit; font-size: 13px; cursor: pointer; transition: all .2s var(--ease); }
.dark .login-recent-chip { background: rgba(201,151,110,.08); color: var(--night-accent); }
.light .login-recent-chip { background: rgba(224,145,90,.08); color: var(--warm-accent2); }
.dark .login-recent-chip:hover { background: rgba(201,151,110,.18); }
.light .login-recent-chip:hover { background: rgba(224,145,90,.18); }

.logout-btn { width: 100%; padding: 10px; border: none; border-radius: var(--radius-sm); cursor: pointer; font-family: inherit; font-size: 13px; text-align: center; transition: all .2s var(--ease); }
.dark .logout-btn { background: rgba(251,113,133,.1); color: #fb7185; }
.light .logout-btn { background: rgba(251,113,133,.08); color: #d44a5c; }
.dark .logout-btn:hover { background: rgba(251,113,133,.2); }
.light .logout-btn:hover { background: rgba(251,113,133,.15); }

/* 设置按钮下拉菜单 */
.settings-btn-wrap { position: relative }

.settings-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  border-radius: 14px;
  min-width: 160px;
  z-index: 50;
  box-shadow: 0 8px 32px rgba(0,0,0,.3);
}
.dark .settings-dropdown { background: rgba(30,28,42,.95); border: 1px solid rgba(255,255,255,.08); backdrop-filter: blur(12px); }
.light .settings-dropdown { background: rgba(255,255,255,.95); border: 1px solid rgba(0,0,0,.08); backdrop-filter: blur(12px); }

.settings-drop-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  transition: all .15s var(--ease);
  white-space: nowrap;
}
.dark .settings-drop-item { background: transparent; color: var(--night-text); }
.light .settings-drop-item { background: transparent; color: #3d2e1e; }
.dark .settings-drop-item:hover { background: rgba(201,151,110,.12); color: var(--night-accent); }
.light .settings-drop-item:hover { background: rgba(224,145,90,.1); color: var(--warm-accent); }

.drop-icon { font-size: 16px; flex-shrink: 0; width: 22px; text-align: center }
.drop-label { flex: 1 }

/* 下拉菜单动画 */
.settings-drop-enter-active { transition: all .2s cubic-bezier(.34,1.56,.64,1) }
.settings-drop-leave-active { transition: all .15s ease-in }
.settings-drop-enter-from { opacity: 0; transform: translateY(-8px) scale(.92) }
.settings-drop-leave-to { opacity: 0; transform: translateY(-4px) scale(.96) }

/* 设置面板子标签 */
.settings-sub-tabs {
  display: flex;
  gap: 4px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}
.settings-sub-tabs::-webkit-scrollbar { display: none }

.settings-sub-tab {
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all .15s var(--ease);
}
.dark .settings-sub-tab { background: transparent; color: var(--night-muted); }
.light .settings-sub-tab { background: transparent; color: #9a8a7a; }
.dark .settings-sub-tab:hover { background: rgba(255,255,255,.04); color: var(--night-text); }
.light .settings-sub-tab:hover { background: rgba(0,0,0,.04); color: #3d2e1e; }
.dark .settings-sub-tab.active { background: rgba(201,151,110,.12); color: var(--night-accent); }
.light .settings-sub-tab.active { background: rgba(224,145,90,.1); color: var(--warm-accent); }

.settings-sub-content { animation: panel-up .25s var(--ease) }

/* 视觉模型选择 */
.vision-model-select { display: flex; flex-direction: column }
.vision-model-label { font-size: 12px; margin-bottom: 6px }
.dark .vision-model-label { color: var(--night-muted); }
.light .vision-model-label { color: #9a8a7a; }

.vision-model-select select.config-input {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
  cursor: pointer;
}

.vision-model-status { margin-top: 8px }
.vision-status-row { display: flex; align-items: center; gap: 8px }
.vision-status-icon { font-size: 14px; width: 20px; text-align: center }
.vision-status-icon.ready { color: #4ade80 }
.vision-status-icon.downloading { color: #f59e0b; animation: spin 1s linear infinite }
.vision-status-text { font-size: 12px }
.dark .vision-status-text { color: var(--night-muted); }
.light .vision-status-text { color: #9a8a7a; }

@keyframes spin { to { transform: rotate(360deg) } }

.vision-download-progress {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
}
.dark .progress-bar { background: rgba(255,255,255,.08); }
.light .progress-bar { background: rgba(0,0,0,.06); }

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width .3s var(--ease);
}
.dark .progress-fill { background: var(--night-accent); }
.light .progress-fill { background: var(--warm-accent); }

.progress-text { font-size: 11px; font-weight: 600; min-width: 36px }
.dark .progress-text { color: var(--night-accent); }
.light .progress-text { color: var(--warm-accent); }

.agreement-overlay { position: fixed; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center; padding: 24px; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); animation: agreement-in .4s var(--ease); }
.dark .agreement-overlay { background: rgba(18,17,26,.8); }
.light .agreement-overlay { background: rgba(254,243,226,.8); }
@keyframes agreement-in { from { opacity: 0; } to { opacity: 1; } }

.agreement-card { position: relative; z-index: 2; width: 100%; max-width: 400px; max-height: 85vh; overflow-y: auto; border-radius: 20px; padding: 28px 24px; animation: agreement-pop .5s var(--ease); }
.dark .agreement-card { background: var(--night-2); border: 1px solid rgba(255,255,255,.06); }
.light .agreement-card { background: #fff; border: 1px solid rgba(0,0,0,.06); box-shadow: 0 8px 40px rgba(0,0,0,.08); }
@keyframes agreement-pop { from { opacity: 0; transform: translateY(20px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }

.agreement-card::-webkit-scrollbar { width: 3px }
.dark .agreement-card::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08); border-radius: 3px; }
.light .agreement-card::-webkit-scrollbar-thumb { background: rgba(0,0,0,.08); border-radius: 3px; }

.agreement-emoji { text-align: center; font-size: 40px; margin-bottom: 8px; }
.agreement-title { text-align: center; font-size: 20px; font-weight: 700; margin-bottom: 6px; }
.agreement-subtitle { text-align: center; font-size: 13px; line-height: 1.6; margin-bottom: 20px; }
.dark .agreement-subtitle { color: var(--night-muted); }
.light .agreement-subtitle { color: #9a8a7a; }
.agreement-subtitle strong { font-weight: 600; }
.dark .agreement-subtitle strong { color: var(--night-accent); }
.light .agreement-subtitle strong { color: var(--warm-accent); }

.agreement-body { margin-bottom: 20px; }
.agreement-intro { font-size: 12px; margin-bottom: 12px; }
.dark .agreement-intro { color: var(--night-muted); }
.light .agreement-intro { color: #9a8a7a; }

.agreement-list { list-style: decimal; padding-left: 20px; display: flex; flex-direction: column; gap: 10px; }
.agreement-list li { font-size: 13px; line-height: 1.6; }
.agreement-list li strong { font-weight: 600; }
.dark .agreement-list li { color: var(--night-text); }
.light .agreement-list li { color: #3d2e1e; }
.dark .agreement-list li strong { color: var(--night-accent); }
.light .agreement-list li strong { color: var(--warm-accent); }

.agreement-footer { text-align: center; }
.agreement-btn { display: inline-block; padding: 12px 36px; border-radius: 99px; border: none; font-family: inherit; font-size: 15px; font-weight: 600; cursor: pointer; transition: all .25s var(--ease); }
.dark .agreement-btn { background: var(--night-accent); color: #1a1510; }
.light .agreement-btn { background: var(--warm-accent); color: #fff; }
.agreement-btn:hover { filter: brightness(1.08); transform: translateY(-1px); }
.agreement-btn:active { transform: translateY(0); }

.confirm-overlay {
  position: fixed; inset: 0; z-index: 30;
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  animation: confirm-in .25s var(--ease);
}
.dark .confirm-overlay { background: rgba(18,17,26,.85); }
.light .confirm-overlay { background: rgba(254,243,226,.85); }
@keyframes confirm-in { from { opacity: 0; } to { opacity: 1; } }

.confirm-card {
  position: relative; z-index: 2;
  width: 100%; max-width: 360px;
  border-radius: 16px; padding: 24px;
  animation: confirm-pop .3s var(--ease);
}
.dark .confirm-card { background: var(--night-2); border: 1px solid rgba(255,255,255,.06); }
.light .confirm-card { background: #fff; border: 1px solid rgba(0,0,0,.06); box-shadow: 0 8px 40px rgba(0,0,0,.1); }
@keyframes confirm-pop { from { opacity: 0; transform: scale(.92) translateY(12px); } to { opacity: 1; transform: scale(1) translateY(0); } }

.confirm-title {
  font-size: 17px; font-weight: 700; margin-bottom: 8px;
}
.dark .confirm-title { color: var(--night-text); }
.light .confirm-title { color: #3d2e1e; }

.confirm-body {
  font-size: 13px; line-height: 1.7; margin-bottom: 20px; white-space: pre-line;
}
.dark .confirm-body { color: var(--night-muted); }
.light .confirm-body { color: #9a8a7a; }

.confirm-actions { display: flex; gap: 10px; justify-content: flex-end; }

.confirm-btn {
  padding: 10px 22px; border: none; border-radius: 99px;
  font-family: inherit; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: all .2s var(--ease);
}
.dark .confirm-btn { background: var(--night-accent); color: #1a1510; }
.light .confirm-btn { background: var(--warm-accent); color: #fff; }
.confirm-btn:hover { filter: brightness(1.1); }

.confirm-btn-cancel {
  background: transparent !important;
}
.dark .confirm-btn-cancel { color: var(--night-muted); border: 1px solid rgba(255,255,255,.12); }
.light .confirm-btn-cancel { color: #9a8a7a; border: 1px solid rgba(0,0,0,.1); }
.confirm-btn-cancel:hover { filter: brightness(1); }
.dark .confirm-btn-cancel:hover { background: rgba(255,255,255,.04) !important; border-color: rgba(255,255,255,.2); }
.light .confirm-btn-cancel:hover { background: rgba(0,0,0,.04) !important; border-color: rgba(0,0,0,.15); }

.confirm-btn-danger { background: rgba(255,59,48,.85) !important; color: #fff !important; }
.dark .confirm-btn-danger { background: rgba(255,59,48,.9) !important; }
.confirm-btn-danger:hover { filter: brightness(1.15) !important; }

.logout-top-btn svg { width: 17px; height: 17px }
.dark .logout-top-btn:hover { background: rgba(251,113,133,.12); color: #fb7185; }
.light .logout-top-btn:hover { background: rgba(251,113,133,.1); color: #d44a5c; }

/* ---- Persona Picker Screen ---- */
.persona-picker-screen {
  position: fixed; inset: 0; z-index: 10;
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.picker-card {
  position: relative; z-index: 2;
  width: 100%; max-width: 480px; max-height: 85vh;
  overflow-y: auto; border-radius: 20px; padding: 28px 24px;
  animation: login-in .5s var(--ease);
}
.dark .picker-card { background: var(--night-2); border: 1px solid rgba(255,255,255,.06); }
.light .picker-card { background: #fff; border: 1px solid rgba(0,0,0,.06); box-shadow: 0 8px 40px rgba(0,0,0,.08); }
.picker-card::-webkit-scrollbar { width: 3px }
.dark .picker-card::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08); border-radius: 3px }
.light .picker-card::-webkit-scrollbar-thumb { background: rgba(0,0,0,.08); border-radius: 3px }

.picker-header { text-align: center; margin-bottom: 24px; }
.picker-emoji { font-size: 40px; margin-bottom: 8px; }
.picker-header h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.picker-header p { font-size: 13px; }
.dark .picker-header p { color: var(--night-muted); }
.light .picker-header p { color: #9a8a7a; }

.picker-groups { display: flex; flex-direction: column; gap: 16px; }
.picker-group-label {
  font-size: 12px; font-weight: 600; padding: 4px 0 8px;
}
.dark .picker-group-label { color: var(--night-accent); }
.light .picker-group-label { color: var(--warm-accent); }
.picker-grid { display: flex; flex-direction: column; gap: 6px; }

.picker-persona {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: var(--radius-sm);
  border: 1px solid transparent; cursor: pointer;
  transition: all .2s var(--ease);
  font-family: inherit; text-align: left; width: 100%;
}
.dark .picker-persona { background: var(--night-3); }
.light .picker-persona { background: var(--warm-1); }
.dark .picker-persona:hover { background: rgba(201,151,110,.1); border-color: rgba(201,151,110,.2); }
.light .picker-persona:hover { background: rgba(224,145,90,.08); border-color: rgba(224,145,90,.15); }
.picker-persona img { width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; }
.picker-persona-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.picker-persona-name { font-size: 14px; font-weight: 600; }
.picker-persona-type { font-size: 11px; }
.dark .picker-persona-type { color: var(--night-accent); }
.light .picker-persona-type { color: var(--warm-accent); }
.picker-persona-bio {
  font-size: 12px; line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dark .picker-persona-bio { color: var(--night-muted); }
.light .picker-persona-bio { color: #9a8a7a; }

.picker-footer { margin-top: 24px; text-align: center; }
.picker-back {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 10px 24px; border-radius: 99px;
  border: 1px solid; cursor: pointer;
  font-family: inherit; font-size: 13px;
  transition: all .2s var(--ease); background: transparent;
}
.dark .picker-back { color: var(--night-muted); border-color: rgba(255,255,255,.1); }
.light .picker-back { color: #9a8a7a; border-color: rgba(0,0,0,.1); }
.dark .picker-back:hover { color: var(--night-text); border-color: rgba(255,255,255,.2); }
.light .picker-back:hover { color: #3d2e1e; border-color: rgba(0,0,0,.2); }

/* ---- Message Tags ---- */
.msg-tag {
  display: inline-block; font-size: 10px; padding: 2px 6px;
  border-radius: 6px; margin-top: 4px;
}
.proactive-tag { background: rgba(139,92,246,.12); color: #a78bfa; }
.status-tag { background: rgba(245,158,11,.12); color: #f59e0b; }
.restart-tag { background: rgba(74,222,128,.12); color: #4ade80; }

/* ---- AI Status State Colors ---- */
.ai-status.ai-busy { color: #f59e0b; }
.ai-status.ai-cooling { color: #94a3b8; }

/* ---- Persona Group Label in Settings ---- */
.persona-group-label {
  font-size: 11px; font-weight: 600; padding: 8px 0 4px;
  text-transform: none; letter-spacing: .02em;
}
.dark .persona-group-label { color: var(--night-accent); }
.light .persona-group-label { color: var(--warm-accent); }
.persona-group-label:first-child { padding-top: 0; }

/* ---- Admin Dashboard ---- */
.admin-dashboard { display: flex; flex-direction: column; height: 100%; }
.admin-topbar { flex-shrink: 0; }
.topbar-brand { font-size: 14px; font-weight: 700; letter-spacing: .01em; }
.dark .topbar-brand { color: var(--night-accent); }
.light .topbar-brand { color: var(--warm-accent); }
.admin-layout { display: flex; flex: 1; overflow: hidden; }

/* 视觉模型状态图标（模态面板内使用） */
.vision-status-icon { font-size: 1rem; }
.vision-status-icon.loaded { color: #4ade80; }
.vision-status-icon.ready { color: #fbbf24; }
.vision-status-icon.downloading,
.vision-status-icon.loading { color: #60a5fa; }
.vision-download-progress { margin-top: 0; }
.vision-download-progress .progress-bar { height: 6px; background: rgba(255,255,255,.1); border-radius: 3px; overflow: hidden; }
.vision-download-progress .progress-fill { height: 100%; background: var(--warm-accent); border-radius: 3px; transition: width .3s; }
.vision-download-progress .progress-text { font-size: .7rem; color: #888; display: block; margin-top: 4px; }

.admin-sidebar {
  width: 220px; flex-shrink: 0; overflow-y: auto; padding: 16px;
  border-right: 1px solid transparent;
}
.dark .admin-sidebar { border-color: rgba(255,255,255,.06); }
.light .admin-sidebar { border-color: rgba(0,0,0,.06); }
.admin-sidebar h4 { font-size: 12px; margin-bottom: 12px; }
.admin-sidebar-empty { font-size: 12px; opacity: .5; padding: 20px 0; text-align: center; }
.admin-user-list { display: flex; flex-direction: column; gap: 6px; }
.admin-user-card {
  display: flex; align-items: center; gap: 10px; padding: 10px;
  border-radius: var(--radius-sm); cursor: pointer; transition: all .15s var(--ease);
  border: 1px solid transparent;
}
.dark .admin-user-card { background: var(--night-2); }
.light .admin-user-card { background: var(--warm-1); }
.admin-user-card:hover { filter: brightness(1.05); }
.admin-user-card.active { border-color: transparent; }
.dark .admin-user-card.active { border-color: var(--night-accent); }
.light .admin-user-card.active { border-color: var(--warm-accent); }
.admin-user-avatar {
  width: 34px; height: 34px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-weight: 700; font-size: 14px;
  flex-shrink: 0;
}
.dark .admin-user-avatar { background: var(--night-4); color: var(--night-text); }
.light .admin-user-avatar { background: var(--warm-2); color: #3d2e1e; }
.admin-user-name { font-size: 13px; font-weight: 600; }
.admin-user-meta { font-size: 11px; opacity: .5; }
.admin-user-info { flex: 1; min-width: 0; }
.admin-user-card { position: relative; }
.admin-user-delete {
  position: absolute; top: 4px; right: 4px; width: 20px; height: 20px;
  border: none; border-radius: 50%; cursor: pointer; font-size: 12px; line-height: 1;
  display: none; align-items: center; justify-content: center;
  opacity: .6; transition: all .15s var(--ease);
}
.dark .admin-user-delete { background: rgba(255,59,48,.2); color: #ff3b30; }
.light .admin-user-delete { background: rgba(255,59,48,.15); color: #c41a1a; }
.admin-user-card:hover .admin-user-delete { display: flex; }
.admin-user-delete:hover { opacity: 1; transform: scale(1.15); }

.admin-main { flex: 1; overflow-y: auto; padding: 20px; }
.admin-main-empty { display: flex; align-items: center; justify-content: center; font-size: 14px; opacity: .3; }

.admin-agent-tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.admin-agent-tab-wrap {
  display: flex; align-items: center; gap: 4px;
}
.admin-agent-tab {
  padding: 6px 14px; border-radius: 99px; border: none; font-family: inherit;
  font-size: 13px; cursor: pointer; transition: all .2s var(--ease);
  font-weight: 500;
}
.dark .admin-agent-tab { background: var(--night-2); color: var(--night-muted); }
.light .admin-agent-tab { background: var(--warm-1); color: #8a7a6a; }
.admin-agent-tab:hover { filter: brightness(1.05); }
.admin-agent-tab.active { font-weight: 600; }
.dark .admin-agent-tab.active { background: var(--night-accent); color: #2b1a0e; }
.light .admin-agent-tab.active { background: var(--warm-accent); color: #fff; }
.admin-agent-delete {
  width: 20px; height: 20px; min-width: 20px; min-height: 20px; border-radius: 50%; border: none; overflow: hidden;
  font-size: 12px; line-height: 20px; cursor: pointer;
  display: none; align-items: center; justify-content: center; padding: 0;
  opacity: .6; transition: all .15s var(--ease); flex: none;
}
.admin-agent-tab-wrap:hover .admin-agent-delete { display: flex; }
.admin-agent-delete:hover { opacity: 1; transform: scale(1.15); }
.dark .admin-agent-delete { background: rgba(255,59,48,.2); color: #ff3b30; }
.light .admin-agent-delete { background: rgba(255,59,48,.15); color: #c41a1a; }

.admin-sections { display: flex; flex-direction: column; gap: 16px; }
.admin-section { padding: 16px; border-radius: 12px; }
.dark .admin-section { background: var(--night-2); }
.light .admin-section { background: var(--warm-1); }
.admin-section h4 { font-size: 13px; font-weight: 600; margin-bottom: 12px; }

.admin-slider-row {
  display: flex; align-items: center; gap: 10px; padding: 6px 0;
  font-size: 13px;
}
.admin-slider-label { width: 36px; flex-shrink: 0; font-weight: 500; }
.admin-slider-row input[type="range"] {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}
.light .admin-slider-row input[type="range"] { background: rgba(0,0,0,.08); }
.dark .admin-slider-row input[type="range"] { background: rgba(255,255,255,.06); }

.admin-slider-row input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all .15s var(--ease);
  box-shadow: 0 2px 6px rgba(0,0,0,.15);
}
.light .admin-slider-row input[type="range"]::-webkit-slider-thumb {
  background: var(--warm-accent);
  border-color: #fff;
}
.dark .admin-slider-row input[type="range"]::-webkit-slider-thumb {
  background: var(--night-accent);
  border-color: var(--night-2);
}
.admin-slider-row input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.15); }

.admin-slider-row input[type="range"]::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.15);
}
.light .admin-slider-row input[type="range"]::-moz-range-thumb { background: var(--warm-accent); }
.dark .admin-slider-row input[type="range"]::-moz-range-thumb { background: var(--night-accent); }

.admin-slider-row input[type="range"]::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: transparent;
}
.light .admin-slider-row input[type="range"]::-moz-range-track { background: rgba(0,0,0,.08); }
.dark .admin-slider-row input[type="range"]::-moz-range-track { background: rgba(255,255,255,.06); }
.admin-slider-val { width: 32px; text-align: right; font-weight: 600; font-size: 12px; flex-shrink: 0; }

.admin-select {
  flex: 1; padding: 6px 8px; border-radius: 8px; font-family: inherit; font-size: 13px;
  border: 1px solid transparent; outline: none;
}
.dark .admin-select { background: var(--night-3); color: var(--night-text); border-color: rgba(255,255,255,.08); }
.light .admin-select { background: var(--warm-1); color: #3d2e1e; border-color: rgba(0,0,0,.08); }

.admin-proactive-btns { display: flex; flex-wrap: wrap; gap: 8px; }
.admin-proactive-btn {
  padding: 8px 14px; border-radius: 10px; border: none; cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 500;
  transition: all .2s var(--ease);
}
.dark .admin-proactive-btn { background: var(--night-3); color: var(--night-text); }
.light .admin-proactive-btn { background: var(--warm-1); color: #3d2e1e; }
.admin-proactive-btn:hover:not(:disabled) { filter: brightness(1.1); }
.admin-proactive-btn:disabled { opacity: .4; cursor: not-allowed; }

.admin-prompt-area {
  width: 100%; padding: 10px 12px; border-radius: var(--radius-sm);
  font-family: 'Cascadia Code', Consolas, monospace; font-size: 11px;
  line-height: 1.5; resize: vertical; outline: none;
  border: 1px solid transparent;
}
.dark .admin-prompt-area { background: var(--night-3); color: var(--night-text); border-color: rgba(255,255,255,.06); }
.light .admin-prompt-area { background: var(--warm-1); color: #3d2e1e; border-color: rgba(0,0,0,.06); }

.admin-chat-section { display: flex; flex-direction: column; }
.admin-chat-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.admin-chat-header h4 { margin-bottom: 0 !important; }
.admin-auto-refresh { display: flex; align-items: center; gap: 6px; font-size: 12px; cursor: pointer; }
.admin-auto-refresh input[type="checkbox"] { accent-color: var(--warm-accent); cursor: pointer; }
.dark .admin-auto-refresh { color: var(--night-muted); }
.light .admin-auto-refresh { color: #9a8a7a; }

.admin-chat-viewer {
  flex: 1; min-height: 200px; max-height: 400px; overflow-y: auto;
  border-radius: 8px; padding: 8px; margin-bottom: 12px;
}
.dark .admin-chat-viewer { background: var(--night-3); border: 1px solid rgba(255,255,255,.06); }
.light .admin-chat-viewer { background: #fff; border: 1px solid rgba(0,0,0,.06); }
.admin-chat-viewer::-webkit-scrollbar { width: 4px; }
.dark .admin-chat-viewer::-webkit-scrollbar-thumb { background: rgba(255,255,255,.1); border-radius: 4px; }
.light .admin-chat-viewer::-webkit-scrollbar-thumb { background: rgba(0,0,0,.1); border-radius: 4px; }

.admin-chat-empty { display: flex; align-items: center; justify-content: center; height: 100%; min-height: 180px; font-size: 13px; opacity: .4; }

.admin-msg-list { display: flex; flex-direction: column; gap: 6px; }
.admin-msg { padding: 8px 10px; border-radius: 8px; font-size: 12px; line-height: 1.5; }
.admin-msg-user { align-self: flex-end; max-width: 75%; }
.dark .admin-msg-user { background: rgba(201,151,110,.12); }
.light .admin-msg-user { background: rgba(224,145,90,.08); }
.admin-msg-ai { align-self: flex-start; max-width: 75%; }
.dark .admin-msg-ai { background: rgba(255,255,255,.04); }
.light .admin-msg-ai { background: rgba(0,0,0,.03); }

.admin-msg-head { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
.admin-msg-sender { font-weight: 600; font-size: 11px; }
.dark .admin-msg-user .admin-msg-sender { color: var(--night-accent); }
.light .admin-msg-user .admin-msg-sender { color: var(--warm-accent); }
.dark .admin-msg-ai .admin-msg-sender { color: var(--night-muted); }
.light .admin-msg-ai .admin-msg-sender { color: #9a8a7a; }
.admin-msg-time { font-size: 10px; opacity: .5; }

.admin-msg-content { word-break: break-word; font-size: 13px; }
.dark .admin-msg-content { color: var(--night-text); }
.light .admin-msg-content { color: #3d2e1e; }

.admin-msg-tag {
  display: inline-block; font-size: 9px; padding: 1px 4px;
  border-radius: 4px; line-height: 1.2;
}

.admin-chat-controls { display: flex; align-items: center; gap: 12px; }
.admin-clear-btn { background: rgba(255,59,48,.15) !important; color: #ff3b30 !important; }
.dark .admin-clear-btn { background: rgba(255,59,48,.2) !important; }
.admin-clear-btn:hover:not(:disabled) { filter: brightness(1.2) !important; }
.admin-chat-count { font-size: 12px; opacity: .5; }
.dark .admin-chat-count { color: var(--night-muted); }
.light .admin-chat-count { color: #9a8a7a; }

.admin-lore-section { max-height: 500px; display: flex; flex-direction: column; }
.admin-lore-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.admin-lore-persona { font-size: 11px; opacity: .5; font-family: monospace; }
.admin-lore-list { overflow-y: auto; flex: 1; }
.admin-lore-entry { margin-bottom: 4px; border-radius: 8px; overflow: hidden; }
.dark .admin-lore-entry { background: rgba(255,255,255,.03); }
.light .admin-lore-entry { background: rgba(0,0,0,.02); }
.admin-lore-entry.lore-disabled { opacity: .45; }
.admin-lore-entry-head { display: flex; align-items: center; gap: 8px; padding: 6px 10px; cursor: pointer; user-select: none; border-radius: 8px; }
.admin-lore-entry-head:hover { background: rgba(255,255,255,.04); }
.admin-lore-toggle { font-size: 10px; width: 16px; flex-shrink: 0; }
.admin-lore-entry-title { font-size: 13px; font-weight: 500; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-lore-entry-priority { font-size: 11px; opacity: .4; font-family: monospace; }
.admin-lore-toggle-btn { background: none; border: 1px solid rgba(255,255,255,.15); color: inherit; border-radius: 4px; padding: 1px 6px; font-size: 11px; cursor: pointer; }
.admin-lore-toggle-btn:hover { background: rgba(255,255,255,.08); }
.admin-lore-entry-body { padding: 8px 12px 12px; }
.admin-lore-row { margin-bottom: 8px; }
.admin-lore-row label { display: block; font-size: 11px; opacity: .6; margin-bottom: 3px; }
.admin-lore-input { width: 100%; border-radius: 6px; border: 1px solid rgba(255,255,255,.1); padding: 6px 10px; font-size: 13px; font-family: inherit; resize: vertical; box-sizing: border-box; }
.dark .admin-lore-input { background: rgba(0,0,0,.3); color: var(--night-text); }
.light .admin-lore-input { background: #fff; color: #3d2e1e; }
.admin-lore-input-sm { width: 80px; }
.admin-lore-keys { font-size: 12px; font-family: monospace; }
.admin-lore-content { font-size: 13px; min-height: 80px; }
.admin-lore-actions { display: flex; gap: 8px; }
.admin-lore-empty { font-size: 12px; opacity: .4; text-align: center; padding: 20px 0; }
.config-btn-sm { padding: 4px 10px; font-size: 12px; }

.admin-sidebar-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.admin-sidebar-tab {
  flex: 1; padding: 8px 0; border: none; border-radius: 8px;
  font-family: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .2s var(--ease);
}
.dark .admin-sidebar-tab { background: var(--night-2); color: var(--night-muted); }
.light .admin-sidebar-tab { background: var(--warm-1); color: #9a8a7a; }
.dark .admin-sidebar-tab.active { background: var(--night-accent); color: #1a1510; }
.light .admin-sidebar-tab.active { background: var(--warm-accent); color: #fff; }

.admin-persona-list { display: flex; flex-direction: column; gap: 6px; }
.admin-persona-card {
  display: flex; align-items: center; gap: 10px; padding: 10px;
  border-radius: var(--radius-sm); cursor: pointer; transition: all .15s var(--ease);
  border: 1px solid transparent;
}
.dark .admin-persona-card { background: var(--night-2); }
.light .admin-persona-card { background: var(--warm-1); }
.admin-persona-card:hover { filter: brightness(1.05); }
.dark .admin-persona-card.active { border-color: var(--night-accent); }
.light .admin-persona-card.active { border-color: var(--warm-accent); }
.admin-persona-avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0; object-fit: cover; cursor: pointer;
}
.admin-persona-avatar-fallback {
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px;
}
.dark .admin-persona-avatar-fallback { background: var(--night-4); color: var(--night-text); }
.light .admin-persona-avatar-fallback { background: var(--warm-2); color: #3d2e1e; }
.admin-persona-info { flex: 1; min-width: 0; }
.admin-persona-name { font-size: 13px; font-weight: 600; }
.admin-persona-meta { font-size: 11px; opacity: .5; }

.admin-persona-editor { max-width: 700px; }
.admin-persona-editor h4 { font-size: 14px; font-weight: 600; margin-bottom: 16px; }
.admin-persona-form { display: flex; gap: 20px; align-items: flex-start; }
.admin-persona-avatar-preview {
  width: 100px; height: 100px; border-radius: 16px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  cursor: pointer;
}
.admin-persona-avatar-preview img { width: 100%; height: 100%; object-fit: cover; }
.dark .admin-persona-avatar-preview { background: var(--night-3); }
.light .admin-persona-avatar-preview { background: var(--warm-2); }
.admin-persona-avatar-fallback-large {
  font-size: 36px; font-weight: 700;
}
.dark .admin-persona-avatar-fallback-large { color: var(--night-muted); }
.light .admin-persona-avatar-fallback-large { color: #9a8a7a; }
.admin-persona-fields { flex: 1; display: flex; flex-direction: column; gap: 10px; }
.admin-persona-field { display: flex; flex-direction: column; gap: 4px; }
.admin-persona-field label { font-size: 12px; font-weight: 600; opacity: .6; }
.admin-persona-input {
  padding: 8px 10px; border-radius: 8px; font-family: inherit; font-size: 13px;
  border: 1px solid transparent; outline: none; transition: border-color .2s var(--ease);
}
.dark .admin-persona-input { background: var(--night-2); color: var(--night-text); border-color: rgba(255,255,255,.08); }
.light .admin-persona-input { background: var(--warm-1); color: #3d2e1e; border-color: rgba(0,0,0,.08); }
.admin-persona-input:focus { border-color: var(--warm-accent); }
.admin-persona-bio { resize: vertical; }
.admin-persona-textarea { resize: vertical; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 12px; line-height: 1.5; width: 100%; box-sizing: border-box; }
.admin-persona-hint { font-size: 11px; opacity: 0.5; margin-top: 2px; }
/* ground_truths 列表编辑器 */
.admin-truth-list { display: flex; flex-direction: column; gap: 4px; }
.admin-truth-row { display: flex; align-items: center; gap: 6px; }
.admin-truth-idx { font-size: 11px; color: #888; min-width: 22px; text-align: right; flex-shrink: 0; }
.admin-truth-input { flex: 1; }
.admin-truth-del { width: 24px; height: 24px; border: none; background: transparent; color: #e74c3c; font-size: 18px; cursor: pointer; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.admin-truth-del:hover { background: #fde8e8; }
.admin-truth-add { border: 1px dashed #aaa; background: transparent; color: #666; font-size: 12px; padding: 6px 12px; border-radius: 6px; cursor: pointer; text-align: left; width: 100%; margin-top: 4px; }
.admin-truth-add:hover { border-color: #667eea; color: #667eea; background: #f5f3ff; }
.dark .admin-truth-idx { color: #777; }
.dark .admin-truth-del:hover { background: rgba(231,76,60,.15); }
.dark .admin-truth-add { border-color: #555; color: #999; }
.dark .admin-truth-add:hover { border-color: #667eea; color: #667eea; background: rgba(102,126,234,.1); }
/* entries (Lorebook) 折叠编辑 */
.admin-entry-row { border-radius: 6px; overflow: hidden; }
.dark .admin-entry-row { background: rgba(255,255,255,.03); }
.light .admin-entry-row { background: rgba(0,0,0,.02); }
.admin-entry-head { display: flex; align-items: center; gap: 6px; padding: 5px 8px; cursor: pointer; user-select: none; }
.admin-entry-head:hover { background: rgba(255,255,255,.04); }
.admin-entry-toggle { font-size: 10px; width: 14px; flex-shrink: 0; opacity: .6; }
.admin-entry-title { font-size: 13px; font-weight: 500; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-entry-priority-text { font-size: 11px; opacity: .4; font-family: monospace; flex-shrink: 0; }
.admin-entry-body { padding: 6px 10px 10px; }
.admin-entry-fields { display: flex; flex-direction: column; gap: 6px; }
.admin-entry-field label { display: block; font-size: 11px; opacity: .6; margin-bottom: 2px; }
.admin-entry-field-row { display: flex; gap: 8px; }
.admin-entry-field-half { flex: 1; }
.admin-persona-actions { display: flex; gap: 8px; margin-top: 4px; }
.config-btn-ghost { background: transparent !important; border: 1px solid rgba(255,255,255,.15) !important; }
.light .config-btn-ghost { border-color: rgba(0,0,0,.15) !important; }

/* ---- 头像放大预览弹窗 ---- */
.avatar-zoom-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,.65);
  display: flex; align-items: center; justify-content: center;
  animation: fadeIn .2s var(--ease);
}
.avatar-zoom-container {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  animation: scaleIn .25s var(--ease);
}
.avatar-zoom-close {
  position: absolute; top: -40px; right: 0;
  width: 32px; height: 32px; border-radius: 50%;
  border: none; background: rgba(255,255,255,.15);
  color: #fff; font-size: 16px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .2s;
}
.avatar-zoom-close:hover { background: rgba(255,255,255,.25); }
.avatar-zoom-image-wrap {
  width: 280px; height: 280px; border-radius: 20px; overflow: hidden;
  border: 3px solid rgba(255,255,255,.2);
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.05);
}
.avatar-zoom-image {
  width: 100%; height: 100%; object-fit: cover;
}
.avatar-zoom-fallback {
  font-size: 80px; font-weight: 700; color: rgba(255,255,255,.3);
}
.avatar-zoom-actions {
  display: flex; gap: 12px;
}
.avatar-upload-btn {
  padding: 10px 20px; border-radius: 10px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  background: rgba(255,255,255,.15); color: #fff;
  border: 1px solid rgba(255,255,255,.2);
  transition: all .2s;
  user-select: none;
}

/* 布局模式 */
.layout-compact .msg-bubble { padding: 6px 10px }
.layout-compact .input-shell { padding: 6px 10px }
.layout-compact .input-shell textarea { min-height: 18px }
.layout-compact .convo { gap: 8px; padding: 10px 0 }
.layout-compact .panel-block { padding: 10px 16px }
.layout-compact .panel-head { padding: 10px 16px }
.layout-compact .profile-body { padding: 16px }
.layout-compact .msg-foot { font-size: 9px; padding: 0 }

.layout-comfortable .msg-bubble { padding: 14px 20px; font-size: 1rem }
.layout-comfortable .input-shell { padding: 12px 16px }
.layout-comfortable .input-shell textarea { font-size: 1rem; min-height: 26px }
.layout-comfortable .convo { gap: 20px; padding: 20px 0 }
.layout-comfortable .panel-block { padding: 22px 24px }
.layout-comfortable .panel-head { padding: 20px 24px }
.layout-comfortable .profile-body { padding: 24px }
.layout-comfortable .msg-foot { font-size: 11px; padding: 0 6px }
.avatar-upload-btn:hover { background: rgba(255,255,255,.25); }
.avatar-upload-btn.loading { opacity: .6; cursor: not-allowed; }
.avatar-upload-msg {
  text-align: center; font-size: 13px; margin: 0;
  color: rgba(255,255,255,.8);
}

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes scaleIn { from { opacity: 0; transform: scale(.9); } to { opacity: 1; transform: scale(1); } }
</style>
