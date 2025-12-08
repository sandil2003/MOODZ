import { ComponentFixture, TestBed } from '@angular/core/testing';

import { JournalAgent } from './journal-agent';

describe('JournalAgent', () => {
  let component: JournalAgent;
  let fixture: ComponentFixture<JournalAgent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [JournalAgent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(JournalAgent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
