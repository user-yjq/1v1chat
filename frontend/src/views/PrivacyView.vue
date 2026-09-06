<template>
  <div class="flex-1 overflow-y-auto p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-2xl border border-gray-200 p-8 space-y-4 text-sm leading-relaxed text-gray-700">
      <h2 class="text-xl font-bold text-gray-800 mb-2">隐私说明</h2>
      <p class="text-xs text-gray-500">最近更新：2026-09-06</p>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">1. 我们收集什么</h3>
        <p>为提供服务，我们存储：登录账号（用户名/昵称）、会话记录（含消息内容）、运行状态（含合规标记）。媒体素材均为内置授权资产，不收集你的照片。</p>
      </section>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">2. 用途边界</h3>
        <p>数据仅用于本产品运行、角色扮演演练与合规复盘；<strong>不会用于模型训练</strong>，不会对外出售或共享你的个人信息。</p>
      </section>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">3. 你的权利</h3>
        <p>你可以随时导出或彻底删除单个对话（删除后不可恢复）；如需要删除账号，请联系管理员处理。</p>
      </section>
      <section>
        <h3 class="font-semibold text-gray-800 mb-1">4. 合规提示</h3>
        <p>请勿在对话中提供真实身份证号、银行卡号、验证码等敏感信息。发现异常内容系统会进行内部标记，仅用于安全与合规处理。</p>
      </section>
      <p class="text-xs text-gray-400 pt-2">
        <router-link to="/terms" class="text-brand-600">查看用户协议</router-link>
        <span class="mx-1">·</span>
        <router-link to="/login" class="text-brand-600">返回登录</router-link>
      </p>
    </div>
  </div>
</template>
