let allCharacters = [];
let currentMergeSource = null;
let currentMergeTarget = null;

document.addEventListener('DOMContentLoaded', function() {
    loadCharacters();
    loadRelationshipNetwork();
    loadMergeSuggestions();
    initCharacterManagement();
});

function initCharacterManagement() {
    document.getElementById('addCharacter').addEventListener('click', () => openCharacterModal());
    document.getElementById('refreshCharacters').addEventListener('click', loadCharacters);
    document.getElementById('refreshNetwork').addEventListener('click', loadRelationshipNetwork);

    document.getElementById('closeModal').addEventListener('click', () => closeModal('characterModal'));
    document.getElementById('cancelCharacter').addEventListener('click', () => closeModal('characterModal'));
    document.getElementById('saveCharacter').addEventListener('click', saveCharacter);

    document.getElementById('closeRelationshipModal').addEventListener('click', () => closeModal('relationshipModal'));
    document.getElementById('cancelRelationship').addEventListener('click', () => closeModal('relationshipModal'));
    document.getElementById('saveRelationship').addEventListener('click', saveRelationship);

    document.getElementById('closeMergeModal').addEventListener('click', () => closeModal('mergeModal'));
    document.getElementById('cancelMerge').addEventListener('click', () => closeModal('mergeModal'));
    document.getElementById('confirmMerge').addEventListener('click', confirmMerge);

    document.getElementById('characterSearch').addEventListener('input', function() {
        filterCharacters(this.value);
    });
}

async function loadCharacters() {
    try {
        const response = await fetch('/api/characters');
        if (!response.ok) throw new Error('加载人物失败');
        const data = await response.json();
        allCharacters = data.characters || [];
        renderCharacterList(allCharacters);
    } catch (error) {
        showToast('加载人物失败: ' + error.message, 'error');
    }
}

function renderCharacterList(characters) {
    const container = document.getElementById('characterList');
    if (!characters || characters.length === 0) {
        container.innerHTML = '<p class="empty-state">暂无人物记录</p>';
        return;
    }
    let html = '<div class="character-grid">';
    characters.forEach(char => {
        html += `
            <div class="character-card" data-id="${char.id}">
                <div class="character-avatar">${getInitials(char.name)}</div>
                <div class="character-info">
                    <h4>${escapeHtml(char.name)}</h4>
                    <p class="character-meta">${char.mentions_count} 次提及${char.platform ? ' · ' + escapeHtml(char.platform) : ''}</p>
                    ${char.description ? `<p class="character-desc">${escapeHtml(char.description.substring(0, 50))}${char.description.length > 50 ? '...' : ''}</p>` : ''}
                    ${char.aliases && char.aliases.length > 0 ? `<p class="character-aliases">别名: ${char.aliases.slice(0, 2).join(', ')}</p>` : ''}
                </div>
                <div class="character-actions">
                    <button class="btn-icon" onclick="viewCharacter('${char.id}')" title="查看">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    </button>
                    <button class="btn-icon" onclick="editCharacter('${char.id}')" title="编辑">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="btn-icon" onclick="addRelationship('${char.id}')" title="添加关系">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    </button>
                    <button class="btn-icon btn-danger" onclick="deleteCharacter('${char.id}')" title="删除">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function filterCharacters(query) {
    if (!query) {
        renderCharacterList(allCharacters);
        return;
    }
    const filtered = allCharacters.filter(char => {
        const name = char.name.toLowerCase();
        const aliases = (char.aliases || []).map(a => a.toLowerCase());
        const desc = (char.description || '').toLowerCase();
        const q = query.toLowerCase();
        return name.includes(q) || aliases.some(a => a.includes(q)) || desc.includes(q);
    });
    renderCharacterList(filtered);
}

async function loadMergeSuggestions() {
    try {
        const response = await fetch('/api/characters/suggestions/merge');
        if (!response.ok) throw new Error('获取合并建议失败');
        const data = await response.json();
        renderMergeSuggestions(data.suggestions || []);
    } catch (error) {
        console.error('获取合并建议失败:', error);
    }
}

function renderMergeSuggestions(suggestions) {
    const container = document.getElementById('mergeSuggestions');
    if (!suggestions || suggestions.length === 0) {
        container.innerHTML = '<p class="empty-state">暂无合并建议</p>';
        return;
    }
    let html = '';
    suggestions.forEach((sug, index) => {
        html += `
            <div class="merge-item-card">
                <div class="merge-info">
                    <span class="merge-name">${escapeHtml(sug.character1_name)}</span>
                    <span class="merge-vs">vs</span>
                    <span class="merge-name">${escapeHtml(sug.character2_name)}</span>
                    <span class="merge-similarity">${(sug.similarity * 100).toFixed(0)}% 相似</span>
                </div>
                <p class="merge-reason">${escapeHtml(sug.reason)}</p>
                <div class="merge-actions">
                    <button class="btn btn-secondary" onclick="openMergeModal('${sug.character1_id}', '${sug.character1_name}', '${sug.character2_id}', '${sug.character2_name}')">合并</button>
                    <button class="btn btn-text" onclick="dismissMergeSuggestion(${index})">忽略</button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

async function loadRelationshipNetwork() {
    try {
        const response = await fetch('/api/relationships/network');
        if (!response.ok) throw new Error('获取关系网络失败');
        const data = await response.json();
        renderRelationshipNetwork(data);
    } catch (error) {
        showToast('加载关系网络失败: ' + error.message, 'error');
    }
}

function renderRelationshipNetwork(data) {
    const svg = document.getElementById('relationshipNetwork');
    const container = document.getElementById('networkContainer');
    if (!data.nodes || data.nodes.length === 0) {
        svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#9ca3af" font-size="14">暂无关系数据</text>';
        return;
    }
    const width = container.clientWidth || 800;
    const height = 400;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;
    const positions = {};
    data.nodes.forEach((node, i) => {
        const angle = (2 * Math.PI * i) / data.nodes.length;
        positions[node.id] = {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle)
        };
    });
    let svgContent = '';
    data.edges.forEach(edge => {
        const source = positions[edge.source];
        const target = positions[edge.target];
        if (source && target) {
            svgContent += `<line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" stroke="#d1d5db" stroke-width="2" opacity="0.6"/>`;
        }
    });
    data.nodes.forEach(node => {
        const pos = positions[node.id];
        svgContent += `
            <g class="network-node" transform="translate(${pos.x}, ${pos.y})" onclick="viewCharacterRelationships('${node.id}')">
                <circle r="24" fill="#8b5cf6" stroke="#fff" stroke-width="2"/>
                <text text-anchor="middle" dy="4" fill="#fff" font-size="12">${getInitials(node.name)}</text>
                <text y="40" text-anchor="middle" fill="#374151" font-size="12">${escapeHtml(node.name.substring(0, 10))}</text>
            </g>
        `;
    });
    svg.innerHTML = svgContent;
}

function openCharacterModal(character = null) {
    const modal = document.getElementById('characterModal');
    const title = document.getElementById('modalTitle');
    document.getElementById('characterId').value = character ? character.id : '';
    document.getElementById('characterName').value = character ? character.name : '';
    document.getElementById('characterAliases').value = character && character.aliases ? character.aliases.join(', ') : '';
    document.getElementById('characterDescription').value = character ? character.description : '';
    document.getElementById('characterPlatform').value = character ? character.platform : '';
    title.textContent = character ? '编辑人物' : '添加人物';
    modal.classList.add('open');
}

async function saveCharacter() {
    const id = document.getElementById('characterId').value;
    const name = document.getElementById('characterName').value.trim();
    const aliasesStr = document.getElementById('characterAliases').value.trim();
    const description = document.getElementById('characterDescription').value.trim();
    const platform = document.getElementById('characterPlatform').value.trim();
    if (!name) {
        showToast('请输入人物姓名', 'error');
        return;
    }
    const aliases = aliasesStr ? aliasesStr.split(',').map(a => a.trim()).filter(a => a) : [];
    const data = { name, aliases, description, platform };
    try {
        let response;
        if (id) {
            response = await fetch(`/api/characters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        } else {
            response = await fetch('/api/characters', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        }
        if (!response.ok) throw new Error(id ? '更新失败' : '创建失败');
        showToast(id ? '人物更新成功' : '人物创建成功', 'success');
        closeModal('characterModal');
        loadCharacters();
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

async function viewCharacter(id) {
    try {
        const response = await fetch(`/api/characters/${id}`);
        if (!response.ok) throw new Error('获取人物详情失败');
        const char = await response.json();
        openCharacterModal(char);
    } catch (error) {
        showToast('加载失败: ' + error.message, 'error');
    }
}

function editCharacter(id) {
    viewCharacter(id);
}

async function deleteCharacter(id) {
    if (!confirm('确定要删除这个人物吗？相关的所有关系也会被删除。')) return;
    try {
        const response = await fetch(`/api/characters/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('删除失败');
        showToast('删除成功', 'success');
        loadCharacters();
        loadRelationshipNetwork();
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

async function addRelationship(sourceId) {
    const modal = document.getElementById('relationshipModal');
    document.getElementById('relationshipSourceId').value = sourceId;
    const select = document.getElementById('relationshipTarget');
    select.innerHTML = '<option value="">选择人物</option>';
    allCharacters.forEach(char => {
        if (char.id !== sourceId) {
            select.innerHTML += `<option value="${char.id}">${escapeHtml(char.name)}</option>`;
        }
    });
    document.getElementById('relationshipType').value = '';
    document.getElementById('relationshipDescription').value = '';
    document.getElementById('relationshipBidirectional').checked = false;
    modal.classList.add('open');
}

async function saveRelationship() {
    const sourceId = document.getElementById('relationshipSourceId').value;
    const targetId = document.getElementById('relationshipTarget').value;
    const type = document.getElementById('relationshipType').value;
    const description = document.getElementById('relationshipDescription').value.trim();
    const bidirectional = document.getElementById('relationshipBidirectional').checked;
    if (!targetId || !type) {
        showToast('请填写完整信息', 'error');
        return;
    }
    try {
        const response = await fetch('/api/relationships', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_id: sourceId, target_id: targetId, type, description, bidirectional })
        });
        if (!response.ok) throw new Error('添加关系失败');
        showToast('关系添加成功', 'success');
        closeModal('relationshipModal');
        loadRelationshipNetwork();
    } catch (error) {
        showToast('添加失败: ' + error.message, 'error');
    }
}

function openMergeModal(sourceId, sourceName, targetId, targetName) {
    currentMergeSource = sourceId;
    currentMergeTarget = targetId;
    document.getElementById('mergeSource').innerHTML = `<strong>${escapeHtml(sourceName)}</strong><span class="merge-label">源</span>`;
    document.getElementById('mergeTarget').innerHTML = `<strong>${escapeHtml(targetName)}</strong><span class="merge-label">目标</span>`;
    document.getElementById('mergeModal').classList.add('open');
}

async function confirmMerge() {
    if (!currentMergeSource || !currentMergeTarget) return;
    try {
        const response = await fetch('/api/characters/merge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_id: currentMergeSource, target_id: currentMergeTarget })
        });
        if (!response.ok) throw new Error('合并失败');
        showToast('合并成功', 'success');
        closeModal('mergeModal');
        loadCharacters();
        loadRelationshipNetwork();
        loadMergeSuggestions();
    } catch (error) {
        showToast('合并失败: ' + error.message, 'error');
    }
}

function viewCharacterRelationships(id) {
    const char = allCharacters.find(c => c.id === id);
    if (char) openCharacterModal(char);
}

function dismissMergeSuggestion(index) {
    console.log('忽略合并建议:', index);
}
