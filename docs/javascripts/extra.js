(function () {
	'use strict';

	let presentationActive = false;
	let currentSlideIndex = 0;
	let slideGroups = [];

	function initMermaid(retries = 25) {
		if (typeof mermaid !== 'undefined') {
			try {
				mermaid.initialize({
					startOnLoad: false,
					theme: 'default',
					securityLevel: 'loose',
					flowchart: { useMaxWidth: true, htmlLabels: true }
				});
				const nodes = document.querySelectorAll('.mermaid:not([data-processed="true"])');
				if (nodes.length > 0) {
					mermaid.run({ nodes: nodes });
				}
			} catch (err) {
				console.error('Mermaid render error:', err);
			}
		} else if (retries > 0) {
			setTimeout(() => initMermaid(retries - 1), 150);
		}
	}

	function getArticleContent() {
		return document.querySelector('article.md-content__inner') ||
			document.querySelector('.md-content__inner') ||
			document.querySelector('article');
	}

	function setupSlides() {
		const article = getArticleContent();
		if (!article) return [];

		const groups = [];
		let currentGroup = [];
		const children = Array.from(article.children);

		for (let i = 0; i < children.length; i++) {
			const el = children[i];
			if (el.id === 'pres-controls') continue;

			if (el.tagName === 'H2') {
				if (currentGroup.length > 0) {
					groups.push(currentGroup);
				}
				currentGroup = [el];
			} else {
				currentGroup.push(el);
			}
		}
		if (currentGroup.length > 0) {
			groups.push(currentGroup);
		}

		groups.forEach((group, gIdx) => {
			group.forEach(el => {
				el.setAttribute('data-pres-slide', String(gIdx));
			});
		});

		return groups;
	}

	function showSlide(index) {
		if (slideGroups.length === 0) return;
		currentSlideIndex = Math.max(0, Math.min(slideGroups.length - 1, index));

		const article = getArticleContent();
		if (!article) return;

		const children = Array.from(article.children);
		children.forEach(el => {
			if (el.id === 'pres-controls') return;
			const slideAttr = el.getAttribute('data-pres-slide');
			if (slideAttr === null) return;

			if (presentationActive) {
				if (slideAttr === String(currentSlideIndex)) {
					el.style.display = '';
				} else {
					el.style.display = 'none';
				}
			} else {
				el.style.display = '';
			}
		});

		updateControls();
		window.scrollTo({ top: 0, behavior: 'instant' });
	}

	function updateControls() {
		const prevBtn = document.getElementById('pres-prev-btn');
		const nextBtn = document.getElementById('pres-next-btn');
		const counter = document.getElementById('pres-counter');
		const titleEl = document.getElementById('pres-current-title');

		if (!prevBtn || !nextBtn || !counter) return;

		const total = slideGroups.length;
		prevBtn.disabled = currentSlideIndex === 0;
		prevBtn.style.opacity = currentSlideIndex === 0 ? '0.2' : '0.85';

		nextBtn.disabled = currentSlideIndex >= total - 1;
		nextBtn.style.opacity = currentSlideIndex >= total - 1 ? '0.2' : '0.85';

		counter.textContent = (currentSlideIndex + 1) + ' / ' + total;

		if (titleEl && slideGroups[currentSlideIndex]) {
			const heading = slideGroups[currentSlideIndex].find(n => n.tagName === 'H2' || n.tagName === 'H1');
			titleEl.textContent = heading ? heading.textContent.replace('¶', '').trim() : '';
		}
	}

	function enterPresentation() {
		slideGroups = setupSlides();
		if (slideGroups.length === 0) return;

		presentationActive = true;
		document.body.classList.add('presentation-mode');
		document.documentElement.classList.add('presentation-mode');

		let controls = document.getElementById('pres-controls');
		if (!controls) {
			controls = document.createElement('div');
			controls.id = 'pres-controls';
			controls.innerHTML =
				'<button id="pres-prev-btn" class="pres-nav-btn pres-left" title="Slide anterior (Seta esquerda)">&#8249;</button>' +
				'<button id="pres-next-btn" class="pres-nav-btn pres-right" title="Proximo slide (Seta direita)">&#8250;</button>' +
				'<div id="pres-bottom-bar">' +
				'<span id="pres-current-title"></span>' +
				'<div class="pres-right-actions">' +
				'<span id="pres-counter"></span>' +
				'<button id="pres-fullscreen-btn" title="Tela cheia">&#x26F6;</button>' +
				'<button id="pres-exit-btn" title="Sair da apresentacao (Esc)">&#10005; Sair</button>' +
				'</div>' +
				'</div>';
			document.body.appendChild(controls);

			document.getElementById('pres-prev-btn').addEventListener('click', () => showSlide(currentSlideIndex - 1));
			document.getElementById('pres-next-btn').addEventListener('click', () => showSlide(currentSlideIndex + 1));
			document.getElementById('pres-exit-btn').addEventListener('click', exitPresentation);
			document.getElementById('pres-fullscreen-btn').addEventListener('click', toggleBrowserFullscreen);
		} else {
			controls.style.display = 'block';
		}

		showSlide(0);
	}

	function exitPresentation() {
		presentationActive = false;
		document.body.classList.remove('presentation-mode');
		document.documentElement.classList.remove('presentation-mode');

		const controls = document.getElementById('pres-controls');
		if (controls) controls.style.display = 'none';

		const article = getArticleContent();
		if (article) {
			Array.from(article.children).forEach(el => {
				if (el.id !== 'pres-controls') {
					el.style.display = '';
				}
			});
		}

		if (slideGroups[currentSlideIndex] && slideGroups[currentSlideIndex][0]) {
			slideGroups[currentSlideIndex][0].scrollIntoView({ behavior: 'smooth' });
		}
	}

	function toggleBrowserFullscreen() {
		if (!document.fullscreenElement) {
			document.documentElement.requestFullscreen().catch(() => { });
		} else {
			if (document.exitFullscreen) {
				document.exitFullscreen().catch(() => { });
			}
		}
	}

	function createFloatingButton() {
		if (document.getElementById('pres-toggle-btn')) return;

		const btn = document.createElement('button');
		btn.id = 'pres-toggle-btn';
		btn.innerHTML = '&#9654; Apresentar';
		btn.title = 'Entrar no modo apresentacao (tecla P)';
		btn.addEventListener('click', () => {
			presentationActive ? exitPresentation() : enterPresentation();
		});
		document.body.appendChild(btn);
	}

	function onKeyDown(e) {
		if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
			return;
		}

		if (e.key === 'p' || e.key === 'P') {
			if (!e.ctrlKey && !e.metaKey && !e.altKey) {
				presentationActive ? exitPresentation() : enterPresentation();
				e.preventDefault();
				return;
			}
		}

		if (!presentationActive) return;

		if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
			showSlide(currentSlideIndex + 1);
			e.preventDefault();
		} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
			showSlide(currentSlideIndex - 1);
			e.preventDefault();
		} else if (e.key === 'Escape') {
			exitPresentation();
			e.preventDefault();
		} else if (e.key === 'f' || e.key === 'F') {
			toggleBrowserFullscreen();
			e.preventDefault();
		}
	}

	function setup() {
		createFloatingButton();
		initMermaid();
	}

	document.addEventListener('keydown', onKeyDown);

	if (window.document$) {
		window.document$.subscribe(() => {
			setup();
		});
	} else if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', setup);
	} else {
		setup();
	}
})();
