const {createApp, ref} = Vue

createApp({
    setup() {
        const searchVal = ref('')
        const mode = ref('search')
        const dots = ref('')
        const resNews = ref({
            title: '',
            content: '',
            url: ''
        })
        const resStatus = ref({
            message: ''
        })

        const search = () => {
            if (searchVal.value.split(" ").length < 30) {
                return alert("Minimum 30 words required to check the news with precision.")
            }
            mode.value = 'processing'
            fetch("/api/text", {
                method: "POST",
                body: JSON.stringify({
                    "text": searchVal.value
                }),
            })
                .then((response) => response.json())
                .then((data) => {
                        resStatus.value.message = data[0][0] > 0.55 ? "correct" : "fake";
                    mode.value = "result";
                    if (resStatus.value.message === "correct") {
                        resNews.value = data[1]
                    }
                })
        }

        setInterval(() => {
            if (dots.value.length === 3) {
                dots.value = ""
            } else {
                dots.value += "."
            }
        }, 500)

        const reload = () => {
            location.reload()
        }

        return {
            searchVal, search, mode, resStatus, dots, resNews, reload
        }
    }
}).mount('#app')
