/**
 * JavaScript para manipulação do formulário de procedimentos
 * com integração ao catálogo de tratamentos
 */
document.addEventListener('DOMContentLoaded', function () {
  // Elementos do DOM
  const categoriaSelect = document.getElementById('categoria_id');
  const tratamentoSelect = document.getElementById('tratamento_id');
  const tratamentoDetalhes = document.getElementById('tratamento_detalhes');
  const tratamentoPreco = document.getElementById('tratamento_preco');
  const tratamentoDuracao = document.getElementById('tratamento_duracao');
  const valorInput = document.getElementById('valor');
  const descricaoInput = document.getElementById('descricao');

  // Verificar se temos todos os elementos necessários
  if (!categoriaSelect || !tratamentoSelect) {
    console.log('Elementos de formulário não encontrados');
    return;
  }

  // Dados dos tratamentos por categoria devem estar em window.tratamentosData
  window.tratamentosData = window.tratamentosData || {};
  // Quando mudar a categoria, atualiza os tratamentos
  categoriaSelect.addEventListener('change', function () {
    const categoriaId = this.value;

    // Limpar e desabilitar o select de tratamentos se nenhuma categoria selecionada
    if (!categoriaId) {
      tratamentoSelect.innerHTML = '<option value="">Selecione uma categoria primeiro...</option>';
      tratamentoSelect.disabled = true;
      if (tratamentoDetalhes) {
        tratamentoDetalhes.classList.add('d-none');
      }
      return;
    }

    // Buscar tratamentos da categoria selecionada
    const tratamentos = window.tratamentosData[categoriaId] || [];

    // Atualizar as opções do select de tratamentos
    tratamentoSelect.innerHTML = '<option value="">Selecione um procedimento...</option>';

    tratamentos.forEach(function (tratamento) {
      const option = document.createElement('option');
      option.value = tratamento.id;
      option.textContent = `${tratamento.nome} - R$ ${parseFloat(tratamento.preco).toFixed(2)}`;
      option.dataset.preco = tratamento.preco;
      option.dataset.duracao = tratamento.duracao;
      tratamentoSelect.appendChild(option);
    });

    // Habilitar o select de tratamentos
    tratamentoSelect.disabled = false;
  });
  // Quando selecionar um tratamento, mostrar detalhes e preencher o valor
  tratamentoSelect.addEventListener('change', function () {
    if (!this.value) {
      if (tratamentoDetalhes) {
        tratamentoDetalhes.classList.add('d-none');
      }
      if (descricaoInput) {
        descricaoInput.disabled = false;
      }
      return;
    }

    const selectedOption = this.options[this.selectedIndex];

    if (selectedOption && selectedOption.dataset) {
      const preco = parseFloat(selectedOption.dataset.preco);
      const duracao = selectedOption.dataset.duracao;

      // Atualizar detalhes se existirem os elementos
      if (tratamentoPreco) {
        tratamentoPreco.textContent = preco.toFixed(2);
      }
      if (tratamentoDuracao) {
        tratamentoDuracao.textContent = duracao || '-';
      }
      if (tratamentoDetalhes) {
        tratamentoDetalhes.classList.remove('d-none');
      }

      // Preencher valor automaticamente
      if (valorInput) {
        valorInput.value = preco.toFixed(2);
      }

      // Desabilitar campo de descrição (já que vem do catálogo)
      if (descricaoInput) {
        descricaoInput.value = '';
        descricaoInput.disabled = true;
      }
    }
  });
  // Alternar entre abas (se existirem)
  const catalogoTab = document.getElementById('catalogo-tab');
  const personalizadoTab = document.getElementById('personalizado-tab');

  if (catalogoTab) {
    catalogoTab.addEventListener('click', function () {
      if (tratamentoSelect && tratamentoSelect.value && descricaoInput) {
        descricaoInput.disabled = true;
      }
    });
  }

  if (personalizadoTab) {
    personalizadoTab.addEventListener('click', function () {
      if (descricaoInput) {
        descricaoInput.disabled = false;
      }
      if (tratamentoSelect) {
        tratamentoSelect.value = '';
      }
      if (tratamentoDetalhes) {
        tratamentoDetalhes.classList.add('d-none');
      }
    });
  }
});

