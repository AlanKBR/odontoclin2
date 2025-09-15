/**
 * Carrega os dados dos tratamentos para uso no formulário de procedimentos
 */
window.tratamentosData = window.tratamentosData || {};

{% for categoria in categorias %}
    window.tratamentosData["{{ categoria.id }}"] = [
    {% for tratamento in categoria.tratamentos %}
        {
            id: {{ tratamento.id }},
            nome: "{{ tratamento.nome }}",
            preco: {{ tratamento.preco }},
            duracao: "{{ tratamento.duracao_estimada|default('-', true) }}"
        }{% if not loop.last %},{% endif %}
    {% endfor %}
    ];
{% endfor %}
