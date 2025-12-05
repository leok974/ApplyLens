# Quick Start: Job-Specific Customization

## What's New?
You can now customize how AI generates your job application answers!

---

## How to Use

### Step 1: Open Settings
1. Click the ApplyLens extension icon in your browser toolbar
2. Navigate to the **Settings** tab

### Step 2: Choose Your Style
Find the "Answer Style" section with two options:

#### Tone
Choose how your answers should sound:
- **Concise & direct**: Straight to the point, no fluff
- **Confident & assertive**: Professional and self-assured (default)
- **Friendly & warm**: Approachable and personable
- **Detailed & explanatory**: Thorough with context

#### Length
Choose how long your answers should be:
- **Short**: 1-3 sentences (quick & punchy)
- **Medium**: 1-2 paragraphs (balanced) (default)
- **Long**: 2-4 paragraphs (comprehensive)

### Step 3: That's It!
Your preferences are saved automatically and will apply to all future form generations.

---

## Examples

### Short + Concise
**Question**: "Why do you want to work here?"
**Answer**: "I'm excited about your AI-first approach to product development and the opportunity to work with cutting-edge LLM technology."

### Medium + Confident
**Question**: "Why do you want to work here?"
**Answer**: "I'm drawn to your company's commitment to building AI products that meaningfully improve how people work. With 5 years of experience in full-stack development and recent deep dives into LangChain and OpenAI APIs, I'm well-positioned to contribute immediately to your engineering team. Your focus on rapid iteration and user feedback aligns perfectly with my product-minded approach to software development."

### Long + Friendly
**Question**: "Why do you want to work here?"
**Answer**: "I've been following your company's journey for the past year, and I'm genuinely excited about the problems you're solving. As someone who's spent the last 5 years building web applications, I've experienced firsthand the challenges of integrating AI into real products—which is exactly what makes your mission so compelling to me.

What really stands out is your emphasis on building tools that developers actually want to use. I appreciate how your engineering blog showcases not just successes but also the messy reality of iterating on AI features. That transparency resonates with me.

On a technical level, I've been working extensively with React, Node.js, and FastAPI, and I recently built a personal project using LangChain to experiment with RAG architectures. I'd love to bring that hands-on experience to your team and learn from engineers who are pushing the boundaries of what's possible with AI."

---

## Tips

### When to Use Each Style

**Concise + Short**
- ✅ Tech screening questions
- ✅ Simple factual questions ("How many years of experience?")
- ✅ When you want to fill forms quickly

**Confident + Medium** (Default)
- ✅ Most job applications
- ✅ Behavioral questions ("Tell us about a challenge...")
- ✅ Balanced between helpful and not overwhelming

**Friendly + Long**
- ✅ Startups with casual culture
- ✅ Cover letters
- ✅ When you want to show personality

**Detailed + Medium**
- ✅ Technical roles
- ✅ Senior positions
- ✅ When explaining complex projects

### Mixing Styles
You can change your style **anytime**:
1. Scan a form with Concise + Short
2. Change to Friendly + Long in Settings
3. Regenerate answers for specific fields

### Pro Tips
- Start with **Confident + Medium** for most jobs
- Switch to **Friendly + Long** for cover letters
- Use **Concise + Short** when time is tight
- Experiment! See what works for your applications

---

## FAQ

**Q: Do I need to set this for every form?**
A: No! Your preferences save automatically and apply to all future forms.

**Q: Can I have different styles for different fields?**
A: Not yet, but it's on our roadmap! For now, you can:
1. Generate answers with Style A
2. Change to Style B in Settings
3. Click "Regenerate" on specific fields

**Q: Will this work for all questions?**
A: Style applies to **narrative questions** (cover letters, "Why interested?", etc.). Contact info (name, email) comes directly from your profile and isn't affected by style.

**Q: What if I don't like the generated answer?**
A: You can:
1. Try a different style and regenerate
2. Edit the answer manually in the panel
3. Uncheck the field to skip auto-filling

**Q: Does this slow down form generation?**
A: No! Preference loading adds <5ms—you won't notice any difference.

---

## Troubleshooting

### Preferences Not Saving
1. Check if you're signed into Chrome (required for sync)
2. Try closing and reopening the popup
3. Check browser console for errors (DevTools → Console)

### Answers Don't Match Style
Backend may not have implemented style handling yet. Check:
1. Open DevTools → Network tab
2. Look for `/api/extension/generate-form-answers` request
3. Verify `style_prefs` appears in request body
4. If yes, contact support—backend needs updating

### Can't Find Settings
1. Click ApplyLens icon in toolbar
2. Look for tabs at top: Overview | Form | DM | **Settings**
3. Scroll down to "Answer Style" section

---

## Feedback

We'd love to hear from you!
- Which styles work best for your applications?
- Should we add more tone options? (e.g., "Technical", "Creative")
- Should we support field-specific styles? (resume vs cover letter)

Send feedback: [your-feedback-email]

---

## What's Next?

Coming soon:
- 🎯 Field-specific styles (different styles for resume vs cover letter)
- 🎨 Style previews (see examples before generating)
- 📊 Success tracking (which styles get more interviews)
- 🤖 Smart suggestions (AI recommends best style for job type)

Stay tuned!
