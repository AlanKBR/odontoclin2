document.addEventListener('DOMContentLoaded', function () {
    // Helpers
    const qs = sel => document.querySelector(sel);
    const pacienteInput = qs('#paciente-autocomplete');
    const pacienteSug = qs('#paciente-suggestions');
    const pacienteHidden = qs('#paciente-id-hidden');
    const tipoSelect = qs('#tipo-atestado');
    const cidInput = qs('#cid-search');
    const cidSug = qs('#cid-suggestions');
    const cidCodigoHidden = qs('#cid-codigo-hidden');
    const cidDescHidden = qs('#cid-desc-hidden');
    const pacienteCpfHidden = qs('#paciente-cpf-hidden');
    const finsSelect = qs('select[name="fins"]');
    const finsOutrosBlock = qs('#fins-outros-block');
    const finsOutrosInput = qs('#fins-outros');
    const textoAtestado = qs('#texto-atestado');

    // Basic guards: if essential elements are missing, abort quietly
    if (!pacienteInput || !textoAtestado) return;

    // Generic suggestion list manager with keyboard support
    function makeSuggManager(inputEl, containerEl, onSelect, fetcher, minLen = 1, delay = 250) {
        let timer = null;
        let items = [];
        let idx = -1;

        inputEl.setAttribute('aria-autocomplete', 'list');
        containerEl.setAttribute('role', 'listbox');

        function clear() { containerEl.innerHTML = ''; items = []; idx = -1; containerEl.style.display = 'none'; }
        function render() {
            containerEl.innerHTML = '';
            if (!items.length) { clear(); return; }
            items.forEach((it, i) => {
                const a = document.createElement('a');
                a.href = '#';
                a.className = 'list-group-item list-group-item-action';
                a.dataset.index = i;
                a.innerHTML = it.html || it.label || '';
                a.addEventListener('click', (e) => { e.preventDefault(); onSelect(it); clear(); });
                containerEl.appendChild(a);
            });
            containerEl.style.display = 'block';
        }

        inputEl.addEventListener('input', function () {
            const q = this.value.trim();
            pacienteHidden && (pacienteHidden.value = '');
            cidCodigoHidden && (cidCodigoHidden.value = '');
            cidDescHidden && (cidDescHidden.value = '');
            clear();
            if (q.length < minLen) return;
            if (timer) clearTimeout(timer);
            timer = setTimeout(() => {
                fetcher(q).then(res => {
                    items = res.slice(0, 50);
                    render();
                }).catch(() => {
                    containerEl.innerHTML = '<div class="text-danger small p-2">Erro ao buscar</div>';
                });
            }, delay);
        });

        inputEl.addEventListener('keydown', function (e) {
            if (!items.length) return;
            if (e.key === 'ArrowDown') { e.preventDefault(); idx = Math.min(idx + 1, items.length - 1); containerEl.children[idx].focus(); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); idx = Math.max(idx - 1, 0); containerEl.children[idx].focus(); }
            else if (e.key === 'Enter') { e.preventDefault(); if (idx >= 0) { const it = items[idx]; onSelect(it); clear(); } }
            else if (e.key === 'Escape') { clear(); }
        });

        // clicking outside closes
        document.addEventListener('click', (ev) => { if (!containerEl.contains(ev.target) && ev.target !== inputEl) clear(); });

        return { clear };
    }

    // Patient fetcher
    const fetchPatients = q => fetch(`/atestados/api/pacientes?q=${encodeURIComponent(q)}`).then(r => r.json()).then(d => d.results.map(r => ({
        label: `${r.nome}${r.cpf ? ' (' + r.cpf + ')' : ''}`,
        html: `${r.nome}${r.cpf ? ' <small class="text-muted">(' + r.cpf + ')</small>' : ''}`,
        id: r.id,
        nome: r.nome,
        cpf: r.cpf
    })));

    makeSuggManager(pacienteInput, pacienteSug, (it) => {
        pacienteInput.value = it.nome;
        pacienteHidden.value = it.id;
        if (pacienteCpfHidden) pacienteCpfHidden.value = it.cpf || '';
    }, fetchPatients, 2, 180);

    // toggle visibility of dias when tipo == comparecimento
    function updateTipoUI() {
        const tipo = tipoSelect.value;
        const diasInput = qs('input[name="dias"]').closest('.mt-2');
        if (diasInput) {
            diasInput.classList.toggle('d-none', tipo === 'comparecimento');
        }
    }
    tipoSelect.addEventListener('change', updateTipoUI);
    updateTipoUI();

    // toggle visibility of 'outros' fins input
    function updateFinsUI() {
        if (!finsSelect) return;
        const isOutros = finsSelect.value === 'outros';
        if (finsOutrosBlock) finsOutrosBlock.classList.toggle('d-none', !isOutros);
    }
    if (finsSelect) {
        finsSelect.addEventListener('change', updateFinsUI);
        updateFinsUI();
    }

    // CID fetcher
    const fetchCid = q => fetch(`/atestados/api/buscar_cid?q=${encodeURIComponent(q)}`).then(r => r.json()).then(d => d.results.map(r => ({
        label: `${r.codigo} - ${r.descricao}`,
        html: `<strong>${r.codigo}</strong> — <span class="small text-muted">${r.descricao}</span>`,
        codigo: r.codigo,
        descricao: r.descricao,
    })));

    makeSuggManager(cidInput, cidSug, (it) => {
        cidInput.value = `${it.codigo} - ${it.descricao}`;
        cidCodigoHidden.value = it.codigo;
        cidDescHidden.value = it.descricao;
    }, fetchCid, 1, 200);

    // helper to round current time to nearest 30min and produce start/end
    function computeTimesNow() {
        const now = new Date();
        let minute = now.getMinutes();
        const remainder = minute % 30;
        let roundedMin;
        if (remainder < 15) roundedMin = minute - remainder;
        else roundedMin = minute + (30 - remainder);
        const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), 0, 0, 0);
        end.setMinutes(roundedMin);
        // if rounding pushes to 60, Date handles overflow
        const start = new Date(end.getTime() - (60 * 60 * 1000));
        const fmt = d => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const fmtDate = d => ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + '/' + d.getFullYear();
        return { start: fmt(start), end: fmt(end), date: fmtDate(end) };
    }

    // fill template button
    qs('#btn-fill-template').addEventListener('click', function () {
        const pacienteNome = pacienteInput.value || '[Nome do Paciente]';
        const pacienteCpf = pacienteCpfHidden ? (pacienteCpfHidden.value || '') : '';
        const pacienteText = pacienteCpf ? `${pacienteNome} portador(a) do CPF ${pacienteCpf}` : pacienteNome;
        const dias = parseInt(qs('input[name="dias"]').value || '1', 10) || 1;
        const finsRaw = finsSelect ? finsSelect.value || '' : '';
        const fins = finsRaw === 'outros' ? (finsOutrosInput && finsOutrosInput.value.trim() ? finsOutrosInput.value.trim() : 'outros') : finsRaw;
        const tipo = tipoSelect.value || 'repouso';
        const cidText = cidCodigoHidden.value ? ` (CID ${cidCodigoHidden.value})` : '';
        let text = '';
        if (tipo === 'comparecimento') {
            const times = computeTimesNow();
            text = `Atesto para ${fins ? 'fins ' + fins + ' que ' : ''}o(a) paciente ${pacienteText} esteve sob tratamento odontológico das ${times.start} as ${times.end} do dia ${times.date}, sendo assim necessitou afastamento de suas atividades normais nesse período.`;
        } else {
            if (fins) {
                const diasText = dias === 1 ? `${dias} dia` : `${dias} dias`;
                text = `Atesto para fins ${fins} que o(a) paciente ${pacienteText} necessita de ${diasText} de repouso${cidText}.`;
            } else {
                const diasText = dias === 1 ? `${dias} dia` : `${dias} dias`;
                text = `Atesto para os devidos fins que o(a) paciente ${pacienteText} necessita de ${diasText} de repouso${cidText}.`;
            }
        }
        textoAtestado.value = text;
    });
});
