# Agent Note: 长短篇写作 references 按作者时刻和读者重组

Status: proposed
Date: 2026-10-17
Related: [开书按作者确认点分段加载](../../implemented/architecture/2026-09-26-opening-by-author-moments.md)、[短篇按作者时刻加载](../../implemented/architecture/2026-09-26-short-write-by-moment.md)、[长篇写作文档精修](../../implemented/bug-fix/2026-10-14-long-write-doc-contract-gaps.md)、[短篇写作资料精修](../../implemented/simplification/2026-10-14-polish-story-short-write.md)

## Problem

10 月 14 日两个写作 skill 的全部 references 已逐份做过句子层面的精修，维护者仍觉得乱。10 月 17 日的多代理审计（5 组分簇通读、守卫约束盘点、网文工作流视角、综合与复核）找到的原因在结构层：

- 工作流文件按作者时刻组织，方法文件按写作课来源堆放，参考索引又用 Phase 1–5。主流程读不到方法：plot-frameworks、commercial-core-methods、style-craft 全仓只有 reference-index 引用，而入口规定写正文不按索引加读。
- 写作端的老规则与去味三件套方向相反。writing-craft 要求「第一个写足，第二个减半」「最重的一句要最短」，narrative-focus 写「不规定递减次数」，deslop-gates 写「不用固定句长、详写比例或最短重拍验收」。写手按老规则写，去味再改回来。
- 模板与检查器、任务包与流程对不上：artifact-protocols 的卷纲模板原样落盘后，`outline_view.py --check --strict` 报 14 个缺作用域行的错误；workflow-volume 无对标时让读 outline-methods 的八节点，volume 任务包不带这份文件；workflow-outline 指向 workflow-daily 里不存在的补建流程；短篇 agent-calls 让写手按 short-craft 执行，写手的 agent-references 里没有这份文件。
- 长短篇共享副本搬运时没有裁剪：短篇钩子文件留着系统激活、副本收获等长篇男频示例；长篇情绪弧线按短篇字数分配；长篇开篇范例取自短篇追妻语料。
- 同一事项多处口径冲突，审计列出 20 多组，例如剧情单元体量有三种口径，感情线阶段有五张表、四套名字，短篇导语有慢放重写和顺接不重演两种做法，短篇平台集合有四套。

## Proposal

按「作者时刻 × 读者」两轴放内容：每个时刻一份流程文件写给主会话，至多一份方法文件，同时是任务包与写手 prompt 的来源。被守卫钉住的文件名保留，把内容迁进去。分批落地，每批跑完守卫再进下一批：

1. 修契约断链：卷纲模板能通过严格检查并加回归；悬空指针、缺细纲处理、追踪说明读取时机、作者记忆查询类别各统一为一种说法；volume 任务包补八节点，outline 任务包补章首章尾钩子类型；短篇派写手时由主会话把题材包要点写进 prompt。缺细纲统一为：写指定章先补建点名章细纲再写并在汇报里说明，日更批内停在该章前问作者，旧细纲只缺字段时照旧字段写、不回写（与部署规则 story-outline 第 7 条和写正文守卫的提示一致）。outline 任务包的钩子表只带名称与公式两列，示例列不进包。组装脚本的题材卡匹配改为最长匹配优先（「玄幻言情」不再把传统玄幻带成辅卡），这一条改变写手拿到的题材卡，随本批一起上。
2. 清理主流程不加载的方法文件：style-craft、plot-frameworks、commercial-core-methods、outline-structure-theory、plot-emotion-system、plot-special-topics 的独有内容逐对比较后迁入权威文件，再删除原文件；新建回炉诊断文件；参考索引改为按时刻和症状查。
3. 规划时刻分层：workflow-volume、workflow-outline 文件内分「主会话」「排纲方法」两节，任务包只截方法节；排纲刻度只在一处定义；outline-methods 承担卷结构与节奏，plot-core-methods 承担细纲与章级方法，long-genre-mechanics 承担核心梗与金手指，character-relations 承担感情线。细纲保留五段，低压章与过场章可写明本章没有高潮及其功能。
4. 写正文热路径与去味三件套对齐：冲突规则改成判据写法，每份文件单独做 A/B，零退步才上线。
5. 题材、人物、女频各留一个权威出处。
6. 短篇重组：writing-workflow 并入 workflow-design，submission-craft 作为平台、导语、字数的唯一出处，钩子文件去掉长篇内容，short-prose-quality 并入 workflow-revision；按题材做构思加正文的配对盲评，零退步才上线。
7. 全部改动文件按五步精修收尾。

书名、简介、平台第一问、数据驱动回炉等新增的作者交互不在本轮。

## Alternatives considered

- **再做一轮逐句精修**：改动面可控，不碰守卫。不采用：10 月 14 日已做过，审计查出的问题集中在文件归属、加载时刻和规则冲突上，句子改得再顺，主流程也读不到方法，冲突也还在。
- **主会话层与方法层拆成新文件**：读者分得最干净。不采用：workflow-volume、workflow-outline 的文件名被作者汇报守卫、契约清单、参考门禁和 story-import 副本钉住；任务包生成器已能按小节截取，文件内分节就能达到同样效果。
- **冷库文件移进归档目录、不再路由**：保留原文备查。不采用：skill 只描述当前状态，不新增顶层目录；留着的文件仍会被检索到，其中的冲突规则还会被模型读到。
- **细纲五段式改成承接、推进、落点三项**：更贴近低压章的实际写法。不采用：消融实验显示决定正文质量的是目标情绪和主角选择两个字段，改五段的收益接近零，代价是检查器、story-import 与作者已有细纲的兼容。

## Consequences

- 收益：每个作者时刻读到的方法与它要填的模板字段一一对应；写作端与去味端不再拉锯；模板能过自己的检查器；长短篇各自只看本侧内容。
- 代价：删除和合并文件要同步 doc-budget、共享资料清单、agent-references、代理模板、适配层与 ClawHub 版本，并递增 agents_version，用户重新部署后才生效；只装 skills 的宿主在升级前仍运行旧副本。热路径与短篇改动需要实测，耗时最长。
- 10 月 14 日两篇精修笔记与 9 月 26 日两篇按时刻加载笔记中，任务包整份带流程、全书体量写在卷纲时刻等事实，落地时另开笔记互链，不在原笔记上改成相反的决定。
