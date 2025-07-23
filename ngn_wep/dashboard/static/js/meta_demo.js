function getSelectedPageId() {
    const select = document.getElementById("pageSelect");
    return select.value || null;
}

function getSelectedAdAccountId() {
    const select = document.getElementById("adAccountSelect");
    return select.value || null;
}

function renderTable(data, targetId, columns) {
    if (!data || data.length === 0) {
        document.getElementById(targetId).innerText = "데이터가 없습니다.";
        return;
    }

    let html = `<table style="color:black;"><thead><tr>`;
    columns.forEach(col => {
        html += `<th style="color:black;">${col.header}</th>`;
    });
    html += "</tr></thead><tbody>";
    data.forEach(row => {
        html += "<tr>";
        columns.forEach(col => {
            let value = row[col.key];
            if (typeof value === "object") {
                value = JSON.stringify(value);
            }
            html += `<td style="color:black;">${value || ""}</td>`;
        });
        html += "</tr>";
    });
    html += "</tbody></table>";

    document.getElementById(targetId).innerHTML = html;
}

async function fetchAndRender(endpoint, targetId) {
    document.getElementById(targetId).innerText = "로딩 중...";
    const res = await fetch("/meta-api/get_data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: endpoint })
    });
    const text = await res.text();

    try {
        const data = JSON.parse(text);
        if (data.error) {
            document.getElementById(targetId).innerText = data.error;
            return;
        }

        const content = data.data || [];

        if (endpoint === "adaccounts") {
            const select = document.getElementById("adAccountSelect");
            select.innerHTML = "";
            content.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.id})`;
                select.appendChild(opt);
            });
            renderTable(content, targetId, [
                { key: "id", header: "ID" },
                { key: "name", header: "이름" }
            ]);
        } else if (endpoint === "businesses") {
            renderTable(content, targetId, [
                { key: "id", header: "ID" },
                { key: "name", header: "비즈니스 이름" }
            ]);
        } else if (endpoint === "pages") {
            const select = document.getElementById("pageSelect");
            select.innerHTML = "";
            content.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.id})`;
                select.appendChild(opt);
            });
            renderTable(content, targetId, [
                { key: "id", header: "페이지 ID" },
                { key: "name", header: "페이지 이름" }
            ]);
        } else if (endpoint.startsWith("campaigns:")) {
            renderTable(content, targetId, [
                { key: "id", header: "캠페인 ID" },
                { key: "name", header: "캠페인 이름" }
            ]);
        } else if (endpoint.startsWith("posts:")) {
            renderTable(content, targetId, [
                { key: "id", header: "게시물 ID" },
                { key: "message", header: "내용" },
                { key: "created_time", header: "작성 시간" }
            ]);
        } else if (endpoint.startsWith("engagement:")) {
            const items = Array.isArray(content.data) ? content.data : content.data?.data || [];
            renderTable(items, targetId, [
                { key: "name", header: "항목명" },
                { key: "period", header: "기간" },
                { key: "values", header: "값" }
            ]);
        } else {
            document.getElementById(targetId).innerHTML = `<pre style="color:black;">${JSON.stringify(content, null, 2)}</pre>`;
        }
    } catch (e) {
        document.getElementById(targetId).innerText = "JSON 파싱 오류\n" + text;
    }
}

async function loadAdAccounts() {
    await fetchAndRender("adaccounts", "adaccounts");
}
async function loadBusinesses() {
    await fetchAndRender("businesses", "businesses");
}
async function loadPages() {
    await fetchAndRender("pages", "pages");
}
async function loadCampaigns() {
    const adAccountId = getSelectedAdAccountId();
    if (!adAccountId) return alert("광고 계정을 먼저 선택하세요");
    await fetchAndRender("campaigns:" + adAccountId, "campaigns");
}
async function loadPosts() {
    const pageId = getSelectedPageId();
    if (!pageId) return alert("페이지를 먼저 선택하세요");
    await fetchAndRender("posts:" + pageId, "posts");
}
async function loadEngagement() {
    const pageId = getSelectedPageId();
    if (!pageId) return alert("페이지를 먼저 선택하세요");
    await fetchAndRender("engagement:" + pageId, "engagement");
}

document.addEventListener("DOMContentLoaded", function () {
    loadAdAccounts();
    loadBusinesses();
    loadPages();
    document.getElementById("loadCampaignsBtn")?.addEventListener("click", loadCampaigns);
    document.getElementById("loadPostsBtn")?.addEventListener("click", loadPosts);
    document.getElementById("loadEngagementBtn")?.addEventListener("click", loadEngagement);
});

