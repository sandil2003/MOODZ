import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';

@Pipe({
    name: 'markdown',
})
export class MarkdownPipe implements PipeTransform {
    constructor(private sanitizer: DomSanitizer) {
        // Configure marked options
        marked.setOptions({
            gfm: true,
            breaks: true,
        });
    }

    transform(value: string | null | undefined): SafeHtml {
        if (!value) {
            return '';
        }

        try {
            // Parse markdown to HTML
            const html = marked.parse(value) as string;
            // Sanitize and return
            return this.sanitizer.bypassSecurityTrustHtml(html);
        } catch (error) {
            console.error('Markdown parsing error:', error);
            return value;
        }
    }
}
