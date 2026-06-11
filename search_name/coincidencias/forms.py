from django import forms


class NameSearchForm(forms.Form):
    query = forms.CharField(
        label="Nombre a buscar",
        max_length=180,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ejemplo: Jhon Peres",
                "autocomplete": "off",
            }
        ),
    )
    min_score = forms.IntegerField(
        label="Coincidencia mínima (%)",
        min_value=0,
        max_value=100,
        required=False,
        initial=45,
    )
    limit = forms.IntegerField(
        label="Máximo de resultados",
        min_value=1,
        max_value=100,
        required=False,
        initial=20,
    )

    def cleaned_or_default(self):
        if not self.is_valid():
            return {"query": "", "min_score": 45, "limit": 20}

        return {
            "query": self.cleaned_data.get("query", "").strip(),
            "min_score": self.cleaned_data.get("min_score") or 45,
            "limit": self.cleaned_data.get("limit") or 20,
        }
