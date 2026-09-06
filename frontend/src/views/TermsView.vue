<template>
  <div class="flex-1 overflow-y-auto p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-2xl border border-gray-200 p-8 space-y-4 text-sm leading-relaxed text-gray-700">
      <h2 class="text-xl font-bold text-gray-800 mb-2">用户协议</h2>
      <p class="text-xs text-gray-500">最近更新：2026-09-06</p>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">1. 产品性质</h3>
        <p>本产品为 AI 角色扮演实验型工具，用于销售陪练、反诈演练、剧情模拟等场景。你在对话中看到的“人”均为 AI 扮演的虚构角色，不是真实人物。</p>
      </section>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">2. 使用约定</h3>
        <p>你同意不将本产品用于针对真实用户的诱导交易、诈骗、骚扰或其他违法违规用途；不使用本产品收集、倒卖真实个人信息；不要求 AI 角色实施任何违法或伤害性行为。</p>
      </section>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">3. 对话内容</h3>
        <p>对话内容仅用于角色扮演演练与内部合规复盘。AI 角色的回答可能包含试探性、夸大或虚构的表述，仅服务于演练目标，不构成任何交易邀约或金融建议。</p>
      </section>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">4. 免责与终止</h3>
        <p>请勿依据对话内容进行真实交易、转账或泄露个人敏感信息。你可以在会话中删除/导出对话（见隐私说明）。</p>
      </section>
      <p class="text-xs text-gray-400 pt-2">
        <router-link to="/privacy" class="text-brand-600">查看隐私说明</router-link>
        <span class="mx-1">·</span>
        <router-link to="/login" class="text-brand-600">返回登录</router-link>
      </p>
    </div>
  </div>
</template>
